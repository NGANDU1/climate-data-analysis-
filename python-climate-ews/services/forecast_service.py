from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd

from models.weather_data import WeatherData

ForecastVariable = Literal["temperature", "humidity", "rainfall"]
ForecastMethod = Literal["naive", "arima"]


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

