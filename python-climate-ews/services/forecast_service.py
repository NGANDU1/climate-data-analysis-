from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd
import os
import requests

from models.weather_data import WeatherData
from models.region import Region

ForecastVariable = Literal["temperature", "humidity", "rainfall"]
ForecastMethod = Literal["naive", "arima"]

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def _as_daily_series(records: list[WeatherData], variable: ForecastVariable) -> pd.Series:
    rows = []
    for r in records:
        rows.append(
            {
                "date": r.timestamp.date() if r.timestamp else None,
                "value": getattr(r, variable, None),
            }
        )
    df = pd.DataFrame(rows).dropna()
    if df.empty:
        return pd.Series(dtype=float)

    daily = df.groupby("date")["value"].mean().sort_index()
    daily.index = pd.to_datetime(daily.index)
    return daily


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _fetch_nasa_power_daily_series(
    *,
    latitude: float,
    longitude: float,
    parameter: str,
    start_date: date,
    end_date: date,
    community: str = "RE",
    time_standard: str = "UTC",
) -> pd.Series:
    url = (
        f"{NASA_POWER_BASE_URL}"
        f"?parameters={parameter}"
        f"&community={community}"
        f"&longitude={longitude}"
        f"&latitude={latitude}"
        f"&start={_yyyymmdd(start_date)}"
        f"&end={_yyyymmdd(end_date)}"
        f"&format=JSON"
        f"&time-standard={time_standard}"
    )
    timeout = float(os.environ.get("EXTERNAL_SYNC_TIMEOUT_SECONDS", "12"))
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json() or {}

    props = payload.get("properties") or {}
    parameter_obj = props.get("parameter") or {}
    series = parameter_obj.get(parameter) or {}

    rows = []
    for day_key, value in series.items():
        if value in (-999, -999.0, None):
            continue
        try:
            d = datetime.strptime(str(day_key), "%Y%m%d").date()
        except Exception:
            continue
        rows.append((pd.to_datetime(d), float(value)))

    if not rows:
        return pd.Series(dtype=float)

    s = pd.Series({d: v for d, v in rows}).sort_index()
    s.index = pd.to_datetime(s.index)
    return s


def _augment_with_nasa_power(series: pd.Series, *, region_id: int, variable: ForecastVariable) -> pd.Series:
    """
    Best-effort: merge NASA POWER daily observations into the local daily series.
    This is used as a fallback when local data is sparse so ARIMA has something to fit.
    """
    enabled = (os.environ.get("NASA_POWER_FORECAST_FALLBACK", "true") or "true").lower() not in {"0", "false", "no"}
    if not enabled:
        return series

    # Only fetch when sparse; keep requests down.
    if not series.empty and len(series) >= 30:
        return series

    region = Region.query.get(region_id)
    if not region or region.latitude is None or region.longitude is None:
        return series

    param = {"temperature": "T2M", "humidity": "RH2M", "rainfall": "PRECTOTCORR"}[variable]

    end = date.today()
    start = end - timedelta(days=180)

    try:
        nasa = _fetch_nasa_power_daily_series(
            latitude=float(region.latitude),
            longitude=float(region.longitude),
            parameter=param,
            start_date=start,
            end_date=end,
        )
    except Exception:
        return series

    if nasa.empty:
        return series

    # Convert NASA daily params into our model units.
    # - PRECTOTCORR is already mm/day
    # - T2M is °C
    # - RH2M is %
    merged = series.copy() if not series.empty else pd.Series(dtype=float)
    for idx, val in nasa.items():
        if idx not in merged.index or pd.isna(merged.loc[idx]):
            merged.loc[idx] = float(val)

    merged = merged.sort_index()
    merged.index = pd.to_datetime(merged.index)
    return merged


def _forecast_naive(series: pd.Series, days: int) -> list[dict]:
    if series.empty:
        base = 0.0
    else:
        base = float(series.iloc[-1])
    start = (series.index.max().date() if not series.empty else date.today()) + timedelta(days=1)
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "value": float(base)}
        for i in range(days)
    ]


def _forecast_arima(series: pd.Series, days: int) -> list[dict]:
    # Optional dependency: statsmodels. If unavailable, caller should fall back.
    from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore

    # Ensure regular daily frequency; interpolate missing days.
    s = series.asfreq("D")
    s = s.interpolate(limit_direction="both")
    if len(s) < 14:
        return _forecast_naive(series, days)

    model = SARIMAX(s, order=(1, 1, 1), enforce_stationarity=False, enforce_invertibility=False)
    res = model.fit(disp=False)
    forecast = res.get_forecast(steps=days).predicted_mean

    start = s.index.max().date() + timedelta(days=1)
    out = []
    for i in range(days):
        out.append({"date": (start + timedelta(days=i)).isoformat(), "value": float(forecast.iloc[i])})
    return out


def forecast_region_variable(
    *,
    region_id: int,
    variable: ForecastVariable,
    days: int = 7,
    method: ForecastMethod = "naive",
) -> dict:
    days = int(days)
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")

    records = (
        WeatherData.query.filter_by(region_id=region_id)
        .order_by(WeatherData.timestamp.desc())
        .limit(2000)
        .all()
    )

    series = _as_daily_series(list(reversed(records)), variable)
    series = _augment_with_nasa_power(series, region_id=region_id, variable=variable)
    if method == "arima":
        try:
            predictions = _forecast_arima(series, days)
            used_method = "arima"
        except Exception:
            predictions = _forecast_naive(series, days)
            used_method = "naive"
    else:
        predictions = _forecast_naive(series, days)
        used_method = "naive"

    history = []
    if not series.empty:
        tail = series.tail(60)
        history = [{"date": d.date().isoformat(), "value": float(v)} for d, v in tail.items()]

    return {
        "success": True,
        "region_id": region_id,
        "variable": variable,
        "method": used_method,
        "days": days,
        "history": history,
        "forecast": predictions,
        "generated_at": datetime.utcnow().isoformat(),
    }
