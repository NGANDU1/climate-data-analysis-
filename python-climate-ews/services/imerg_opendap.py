from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import requests

from models import db
from models.dataset import Dataset
from models.external_sync_run import ExternalSyncRun
from models.region import Region
from models.weather_data import WeatherData


CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


@dataclass(frozen=True)
class SyncResult:
    dataset_id: int
    rows_received: int
    rows_imported: int
    rows_skipped: int
    source: str
    notes: str


def _env(name: str) -> str | None:
    v = os.environ.get(name)
    return v.strip() if v and v.strip() else None


def _earthdata_session() -> requests.Session:
    """
    Create a requests session authenticated for Earthdata.

    Supported env vars:
      - EARTHDATA_TOKEN (preferred)
      - EARTHDATA_USERNAME + EARTHDATA_PASSWORD
    """
    token = _env("EARTHDATA_TOKEN")
    username = _env("EARTHDATA_USERNAME")
    password = _env("EARTHDATA_PASSWORD")

    if not token and not (username and password):
        raise ValueError("Missing Earthdata credentials. Set EARTHDATA_TOKEN or EARTHDATA_USERNAME/EARTHDATA_PASSWORD.")

    s = requests.Session()
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    if username and password:
        s.auth = (username, password)
    return s


def _cmr_granules_for_range(
    *,
    short_name: str,
    version: str,
    start_date: date,
    end_date: date,
    page_size: int = 2000,
) -> list[dict[str, Any]]:
    # CMR uses inclusive temporal queries; use end+1 day to ensure full coverage.
    start_dt = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).isoformat() + "Z"

    params = {
        "short_name": short_name,
        "version": version,
        "temporal": f"{start_dt},{end_dt}",
        "page_size": str(page_size),
        "sort_key": "-start_date",
    }
    resp = requests.get(CMR_GRANULES_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return (payload.get("feed") or {}).get("entry") or []


def _pick_opendap_url(entry: dict[str, Any]) -> str | None:
    links = entry.get("links") or []
    for link in links:
        href = (link or {}).get("href") or ""
        title = ((link or {}).get("title") or "").lower()
        # Heuristics: look for explicit OPeNDAP links first.
        if "opendap" in title and href.startswith("http"):
            return href
    for link in links:
        href = (link or {}).get("href") or ""
        if "opendap" in href.lower() and href.startswith("http"):
            return href
    return None


def _parse_ascii_numbers(text: str) -> list[float]:
    # Hyrax .ascii responses include headers; extract floats robustly.
    nums = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", text)
    out: list[float] = []
    for n in nums:
        try:
            out.append(float(n))
        except Exception:
            continue
    return out


def _extract_ascii_grid_values(text: str, var_name: str) -> list[float]:
    """
    Extract numeric values for a grid's data array from a Hyrax .ascii response.

    OPeNDAP ASCII often includes map vectors (lat/lon/time) alongside the array.
    This function heuristically keeps only lines that look like the data array and
    excludes map lines.
    """
    values: list[float] = []
    in_data = False
    vn = var_name.lower()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("--------------------------------"):
            in_data = True
            continue
        if not in_data:
            continue

        l = line.lower()
        # Exclude map vectors
        if ".lat" in l or ".lon" in l or ".time" in l:
            continue
        if l.startswith("lat[") or l.startswith("lon[") or l.startswith("time["):
            continue

        # Keep lines that start with the variable name (grid name) or its array member.
        if not (l.startswith(vn) or l.startswith(f"{vn}.{vn}") or l.startswith(f"/{vn}")):
            continue

        parts = line.split(None, 1)
        if len(parts) != 2:
            continue

        values.extend(_parse_ascii_numbers(parts[1]))

    return values


def _query_point_mean_precip_mm_day(
    *,
    session: requests.Session,
    opendap_url: str,
    lat: float,
    lon: float,
    box_deg: float = 0.1,
) -> float | None:
    """
    Query a tiny lat/lon window via geogrid() and compute the mean precipitation in that window.

    Uses Hyrax ASCII response to avoid netCDF/HDF dependencies.
    """
    top = lat + box_deg / 2.0
    bottom = lat - box_deg / 2.0
    left = lon - box_deg / 2.0
    right = lon + box_deg / 2.0

    variables_to_try = ["precipitation", "precipitationCal", "precipitationCal_day", "precipitationCalDay"]

    for var in variables_to_try:
        query = f"geogrid({var},{top},{left},{bottom},{right})"
        ascii_url = f"{opendap_url}.ascii?{query}"

        r = session.get(ascii_url, timeout=60)
        if r.status_code in (401, 403):
            raise PermissionError("Earthdata authorization failed (401/403). Ensure your account is authorized for GES DISC and/or token is valid.")
        if not r.ok:
            continue

        nums = _extract_ascii_grid_values(r.text, var)
        # Filter out fill values if present.
        cleaned = [x for x in nums if x not in (-9999.0, -999.0, -99.0, -999.9, -9999.9)]
        if not cleaned:
            continue
        return float(sum(cleaned) / len(cleaned))

    return None


def sync_gpm_imerg_daily_point(
    *,
    start_date: date,
    end_date: date,
    short_name: str = "GPM_3IMERGDF",
    version: str = "07",
    box_deg: float = 0.1,
) -> SyncResult:
    """
    Sync GPM IMERG Final Daily rainfall using OPeNDAP point subsetting.

    Stores rainfall-only rows in weather_data with source="gpm_imerg".
    """
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    source = "gpm_imerg"
    notes = f"GPM IMERG daily sync {short_name} v{version} {start_date.isoformat()}..{end_date.isoformat()}"

    run = ExternalSyncRun(source=source, status="running", started_at=datetime.utcnow(), message=notes)
    db.session.add(run)
    db.session.commit()

    dataset = Dataset(
        name=f"GPM IMERG ({short_name} v{version}) {start_date.isoformat()} to {end_date.isoformat()}",
        source_type="api_json",
        notes=notes,
        uploaded_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.flush()

    session = _earthdata_session()

    entries = _cmr_granules_for_range(short_name=short_name, version=version, start_date=start_date, end_date=end_date)
    rows_received = len(entries)

    # Pick at most one granule per date (CMR can return multiple).
    by_day: dict[date, dict[str, Any]] = {}
    for e in entries:
        ts = e.get("time_start") or e.get("time_start")  # keep simple
        try:
            d = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
        except Exception:
            continue
        by_day.setdefault(d, e)

    regions: list[Region] = Region.query.all()
    rows_imported = 0
    rows_skipped = 0

    for d in sorted(by_day.keys()):
        entry = by_day[d]
        opendap_url = _pick_opendap_url(entry)
        if not opendap_url:
            rows_skipped += 1
            continue

        for region in regions:
            if region.latitude is None or region.longitude is None:
                rows_skipped += 1
                continue

            # Avoid duplicates for this region/day/source.
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            exists = (
                WeatherData.query.filter(WeatherData.region_id == region.id)
                .filter(WeatherData.source == source)
                .filter(WeatherData.timestamp >= start_dt)
                .filter(WeatherData.timestamp < end_dt)
                .first()
            )
            if exists:
                rows_skipped += 1
                continue

            try:
                precip = _query_point_mean_precip_mm_day(
                    session=session,
                    opendap_url=opendap_url,
                    lat=float(region.latitude),
                    lon=float(region.longitude),
                    box_deg=box_deg,
                )
            except PermissionError as e:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.message = str(e)
                db.session.commit()
                raise
            except Exception:
                precip = None

            if precip is None:
                rows_skipped += 1
                continue

            db.session.add(
                WeatherData(
                    region_id=region.id,
                    dataset_id=dataset.id,
                    source=source,
                    rainfall=float(precip),
                    timestamp=start_dt,
                )
            )
            rows_imported += 1

        db.session.commit()

    dataset.rows_received = rows_received
    dataset.rows_imported = rows_imported
    dataset.rows_skipped = rows_skipped
    db.session.commit()

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
