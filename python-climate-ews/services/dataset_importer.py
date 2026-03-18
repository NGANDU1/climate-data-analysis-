from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Iterable

import pandas as pd
import re

from models import db
from models.dataset import Dataset
from models.region import Region
from models.weather_data import WeatherData


@dataclass(frozen=True)
class ImportResult:
    dataset: Dataset
    rows_received: int
    rows_imported: int
    rows_skipped: int
    skipped_reasons_sample: list[dict[str, Any]]


_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "region": ["region", "region_name", "province", "province_name", "area"],
    "region_id": ["region_id", "regionid", "province_id", "region id", "province id"],
    "timestamp": ["timestamp", "time", "datetime", "date", "day", "observed_at"],
    "temperature": ["temperature", "temp", "t", "temp_c", "temperature_c"],
    "humidity": ["humidity", "hum", "rh", "relative_humidity"],
    "rainfall": ["rainfall", "rain", "precip", "precipitation", "precip_mm"],
    "wind_speed": ["wind_speed", "wind", "wind_kph", "wind_kmh"],
    "pressure": ["pressure", "press", "pressure_hpa"],
}


def _norm_col_name(name: str) -> str:
    n = str(name)
    n = n.lstrip("\ufeff").strip().lower()
    n = re.sub(r"\s+", "_", n)
    return n


def _pick_col(df: pd.DataFrame, canonical: str) -> str | None:
    cols = {_norm_col_name(c): c for c in df.columns}
    for alias in _COLUMN_SYNONYMS.get(canonical, []):
        if _norm_col_name(alias) in cols:
            return str(cols[_norm_col_name(alias)])
    return None


def _coerce_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        if isinstance(val, str) and not val.strip():
            return None
        return float(val)
    except Exception:
        return None


def _is_valid_row(
    temperature: float | None,
    humidity: float | None,
    rainfall: float | None,
    wind_speed: float | None,
    pressure: float | None,
) -> tuple[bool, str | None]:
    # Keep ranges permissive; focus on catching obvious data errors.
    if temperature is not None and not (-50 <= temperature <= 60):
        return False, "temperature_out_of_range"
    if humidity is not None and not (0 <= humidity <= 100):
        return False, "humidity_out_of_range"
    if rainfall is not None and not (0 <= rainfall <= 500):
        return False, "rainfall_out_of_range"
    if wind_speed is not None and not (0 <= wind_speed <= 250):
        return False, "wind_speed_out_of_range"
    if pressure is not None and not (800 <= pressure <= 1100):
        return False, "pressure_out_of_range"
    return True, None


def import_dataset_from_dataframe(
    *,
    df: pd.DataFrame,
    name: str,
    source_type: str,
    original_filename: str | None = None,
    notes: str | None = None,
    default_region_id: int | None = None,
    create_missing_regions: bool = False,
) -> ImportResult:
    if df is None or df.empty:
        raise ValueError("Dataset is empty")

    region_col = _pick_col(df, "region")
    region_id_col = _pick_col(df, "region_id")
    ts_col = _pick_col(df, "timestamp")
    temp_col = _pick_col(df, "temperature")
    hum_col = _pick_col(df, "humidity")
    rain_col = _pick_col(df, "rainfall")
    wind_col = _pick_col(df, "wind_speed")
    press_col = _pick_col(df, "pressure")

    if ts_col is None:
        raise ValueError("Could not find a timestamp/date column")

    if region_col is None and region_id_col is None and default_region_id is None:
        raise ValueError("Missing region column and no default region provided")

    dataset = Dataset(
        name=name.strip() or "Uploaded dataset",
        source_type=source_type,
        original_filename=original_filename,
        notes=notes,
        uploaded_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.flush()  # allocate dataset.id

    rows_received = int(len(df))
    rows_imported = 0
    rows_skipped = 0
    skipped_sample: list[dict[str, Any]] = []

    regions_by_name: dict[str, Region] = {}
    regions_by_id: dict[int, Region] = {}
    if region_col is not None or region_id_col is not None:
        existing = Region.query.all()
        regions_by_name = {r.name.strip().lower(): r for r in existing if r.name}
        regions_by_id = {int(r.id): r for r in existing if r.id is not None}

    objects: list[WeatherData] = []

    # Parse timestamps up-front (vectorized). Keep original order.
    ts_series = pd.to_datetime(df[ts_col], errors="coerce", utc=False)

    for idx, row in df.iterrows():
        ts = ts_series.iloc[idx]
        if pd.isna(ts):
            rows_skipped += 1
            if len(skipped_sample) < 25:
                skipped_sample.append({"row_index": int(idx), "reason": "invalid_timestamp"})
            continue

        if region_col is not None:
            region_name = str(row.get(region_col, "")).strip()
            key = region_name.lower()
            region = regions_by_name.get(key)
            if not region and create_missing_regions and region_name:
                region = Region(name=region_name, latitude=0.0, longitude=0.0, risk_level="low")
                db.session.add(region)
                db.session.flush()
                regions_by_name[key] = region
            if not region:
                rows_skipped += 1
                if len(skipped_sample) < 25:
                    skipped_sample.append({"row_index": int(idx), "reason": "unknown_region", "region": region_name})
                continue
            region_id = region.id
        elif region_id_col is not None:
            raw = row.get(region_id_col)
            try:
                region_id = int(raw)
            except Exception:
                rows_skipped += 1
                if len(skipped_sample) < 25:
                    skipped_sample.append({"row_index": int(idx), "reason": "invalid_region_id", "region_id": raw})
                continue

            region = regions_by_id.get(region_id)
            if not region:
                rows_skipped += 1
                if len(skipped_sample) < 25:
                    skipped_sample.append({"row_index": int(idx), "reason": "unknown_region_id", "region_id": region_id})
                continue
        else:
            region_id = int(default_region_id)

        temperature = _coerce_float(row.get(temp_col)) if temp_col else None
        humidity = _coerce_float(row.get(hum_col)) if hum_col else None
        rainfall = _coerce_float(row.get(rain_col)) if rain_col else None
        wind_speed = _coerce_float(row.get(wind_col)) if wind_col else None
        pressure = _coerce_float(row.get(press_col)) if press_col else None

        ok, reason = _is_valid_row(temperature, humidity, rainfall, wind_speed, pressure)
        if not ok:
            rows_skipped += 1
            if len(skipped_sample) < 25:
                skipped_sample.append({"row_index": int(idx), "reason": reason})
            continue

        # Require at least one primary signal to avoid inserting empty rows.
        if temperature is None and humidity is None and rainfall is None:
            rows_skipped += 1
            if len(skipped_sample) < 25:
                skipped_sample.append({"row_index": int(idx), "reason": "missing_primary_values"})
            continue

        objects.append(
            WeatherData(
                region_id=region_id,
                dataset_id=dataset.id,
                source="upload",
                temperature=temperature,
                humidity=humidity,
                rainfall=rainfall,
                wind_speed=wind_speed,
                pressure=pressure,
                timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
            )
        )
        rows_imported += 1

    if objects:
        db.session.bulk_save_objects(objects)

    dataset.rows_received = rows_received
    dataset.rows_imported = rows_imported
    dataset.rows_skipped = rows_skipped
    db.session.commit()

    return ImportResult(
        dataset=dataset,
        rows_received=rows_received,
        rows_imported=rows_imported,
        rows_skipped=rows_skipped,
        skipped_reasons_sample=skipped_sample,
    )


def import_dataset_from_upload(
    *,
    file_bytes: bytes,
    filename: str,
    name: str,
    notes: str | None = None,
    default_region_id: int | None = None,
    create_missing_regions: bool = False,
) -> ImportResult:
    lower = filename.lower()
    if lower.endswith(".csv"):
        # Some open-data exports use a key/value metadata header followed by (timestamp,value) rows.
        # Detect and convert those into the standard dataframe shape.
        parsed = _try_parse_keyvalue_timeseries_csv(file_bytes)
        if parsed is not None:
            df = parsed
        else:
            df = pd.read_csv(BytesIO(file_bytes))
        source_type = "csv"
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        # pandas requires openpyxl (xlsx) or xlrd (xls). Keep error explicit.
        df = pd.read_excel(BytesIO(file_bytes))
        source_type = "excel"
    else:
        raise ValueError("Unsupported file type. Please upload CSV or Excel (.xlsx/.xls).")

    return import_dataset_from_dataframe(
        df=df,
        name=name,
        source_type=source_type,
        original_filename=filename,
        notes=notes,
        default_region_id=default_region_id,
        create_missing_regions=create_missing_regions,
    )


def _try_parse_keyvalue_timeseries_csv(file_bytes: bytes) -> pd.DataFrame | None:
    """
    Supports CSV exports shaped like:
      location,Basel
      lat,47.75
      lon,7.5
      variable,Temperature
      ...
      timestamp,Some Label
      20250101T0000,-1.10
      20250101T0100,-1.29

    Returns a dataframe with columns: region, timestamp, <variable>.
    """
    try:
        text = file_bytes.decode("utf-8-sig", errors="replace")
    except Exception:
        return None

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 10:
        return None

    if not lines[0].lower().startswith("location,"):
        return None

    meta: dict[str, str] = {}
    data_started = False
    data_rows: list[tuple[str, str]] = []

    for ln in lines[:200000]:
        parts = [p.strip() for p in ln.split(",", 1)]
        if len(parts) != 2:
            continue
        k, v = parts[0], parts[1]

        if not data_started:
            meta[_norm_col_name(k)] = v
            if _norm_col_name(k) == "timestamp":
                data_started = True
            continue

        # data rows
        data_rows.append((k, v))

    if not data_rows:
        return None

    # Detect timestamp format like YYYYMMDDTHHMM
    if not re.fullmatch(r"\d{8}T\d{4}", data_rows[0][0].strip()):
        return None

    location = (meta.get("location") or "").strip() or "Imported location"
    variable = (meta.get("variable") or "").strip().lower()

    target_col = "temperature"
    if "humid" in variable or variable in {"rh", "humidity"}:
        target_col = "humidity"
    elif "rain" in variable or "precip" in variable:
        target_col = "rainfall"

    records: list[dict[str, Any]] = []
    for ts_raw, val_raw in data_rows:
        ts_raw = ts_raw.strip()
        try:
            ts = datetime.strptime(ts_raw, "%Y%m%dT%H%M")
        except Exception:
            continue
        try:
            val = float(val_raw)
        except Exception:
            continue
        records.append({"region": location, "timestamp": ts, target_col: val})

    if not records:
        return None

    return pd.DataFrame(records)


def import_dataset_from_records(
    *,
    records: Iterable[dict[str, Any]],
    name: str,
    notes: str | None = None,
    default_region_id: int | None = None,
    create_missing_regions: bool = False,
) -> ImportResult:
    df = pd.DataFrame(list(records))
    return import_dataset_from_dataframe(
        df=df,
        name=name,
        source_type="api_json",
        original_filename=None,
        notes=notes,
        default_region_id=default_region_id,
        create_missing_regions=create_missing_regions,
    )
