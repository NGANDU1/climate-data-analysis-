from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests

from models import db
from models.dataset import Dataset
from models.external_sync_run import ExternalSyncRun
from models.region import Region
from models.weather_data import WeatherData


NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


@dataclass(frozen=True)
class SyncResult:
    dataset_id: int
    rows_received: int
    rows_imported: int
    rows_skipped: int
    source: str
    notes: str


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_power_payload(payload: dict, *, params: list[str]) -> dict[str, dict[str, float | None]]:
    """
    Returns: { 'YYYYMMDD': { 'T2M': 12.3, ... } }
    POWER JSON structure is typically:
      properties.parameter.<PARAM>.<YYYYMMDD> = value
    """
    props = payload.get("properties") or {}
    parameter = props.get("parameter") or {}
    by_day: dict[str, dict[str, float | None]] = {}

    for p in params:
        series = parameter.get(p) or {}
        for day_key, value in series.items():
            by_day.setdefault(day_key, {})[p] = None if value in (-999, -999.0, None) else float(value)

    return by_day


def sync_nasa_power_daily(
    *,
    start_date: date,
    end_date: date,
    community: str = "RE",
    parameters: list[str] | None = None,
    time_standard: str = "UTC",
    track_run: bool = True,
) -> SyncResult:
    """
    Pull NASA POWER daily time-series for each Region (lat/lon) and store into weather_data.

    Notes:
    - Uses per-region point requests; keep date spans reasonable to avoid rate limiting.
    - Requires regions to have latitude/longitude set.
    """
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    if parameters is None:
        parameters = ["T2M", "RH2M", "PRECTOTCORR", "WS10M", "PS"]

    source = "nasa_power"
    notes = f"NASA POWER daily sync ({community}) {start_date.isoformat()}..{end_date.isoformat()}"

    run = None
    if track_run:
        run = ExternalSyncRun(source=source, status="running", started_at=datetime.utcnow(), message=notes)
        db.session.add(run)
        db.session.commit()

    dataset = Dataset(
        name=f"NASA POWER ({start_date.isoformat()} to {end_date.isoformat()})",
        source_type="api_json",
        original_filename=None,
        notes=notes,
        uploaded_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.flush()

    regions: list[Region] = Region.query.all()
    rows_received = 0
    rows_imported = 0
    rows_skipped = 0

    timeout = float(os.environ.get("EXTERNAL_SYNC_TIMEOUT_SECONDS", "30"))

    for region in regions:
        if region.latitude is None or region.longitude is None:
            rows_skipped += 1
            continue

        url = (
            f"{NASA_POWER_BASE_URL}"
            f"?parameters={','.join(parameters)}"
            f"&community={community}"
            f"&longitude={region.longitude}"
            f"&latitude={region.latitude}"
            f"&start={_yyyymmdd(start_date)}"
            f"&end={_yyyymmdd(end_date)}"
            f"&format=JSON"
            f"&time-standard={time_standard}"
        )

        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            rows_skipped += 1
            if run is not None:
                run.message = (run.message or "") + f"\nRegion {region.name}: request failed ({e})"
                db.session.commit()
            continue

        by_day = _parse_power_payload(payload, params=parameters)
        rows_received += len(by_day)

        # Existing timestamps in range for this region/source (avoid duplicates).
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        existing = (
            db.session.query(WeatherData.timestamp)
            .filter(WeatherData.region_id == region.id)
            .filter(WeatherData.source == source)
            .filter(WeatherData.timestamp >= start_dt)
            .filter(WeatherData.timestamp < end_dt)
            .all()
        )
        existing_set = {x[0].date() for x in existing if x and x[0]}

        objects: list[WeatherData] = []
        for day_key, values in by_day.items():
            # NASA POWER uses YYYYMMDD keys.
            try:
                d = datetime.strptime(day_key, "%Y%m%d").date()
            except Exception:
                rows_skipped += 1
                continue

            if d in existing_set:
                rows_skipped += 1
                continue

            temperature = values.get("T2M")
            humidity = values.get("RH2M")
            rainfall = values.get("PRECTOTCORR")
            wind_speed = values.get("WS10M")
            pressure_kpa = values.get("PS")
            pressure_hpa = (pressure_kpa * 10.0) if pressure_kpa is not None else None

            if temperature is None and humidity is None and rainfall is None:
                rows_skipped += 1
                continue

            objects.append(
                WeatherData(
                    region_id=region.id,
                    dataset_id=dataset.id,
                    source=source,
                    temperature=temperature,
                    humidity=humidity,
                    rainfall=rainfall,
                    wind_speed=wind_speed,
                    pressure=pressure_hpa,
                    timestamp=datetime.combine(d, datetime.min.time()),
                )
            )
            rows_imported += 1

        if objects:
            db.session.bulk_save_objects(objects)
            db.session.commit()

    dataset.rows_received = rows_received
    dataset.rows_imported = rows_imported
    dataset.rows_skipped = rows_skipped
    db.session.commit()

    if run is not None:
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.dataset_id = dataset.id
        run.rows_received = rows_received
        run.rows_imported = rows_imported
        run.rows_skipped = rows_skipped
        db.session.commit()

    return SyncResult(
        dataset_id=dataset.id,
        rows_received=rows_received,
        rows_imported=rows_imported,
        rows_skipped=rows_skipped,
        source=source,
        notes=notes,
    )
