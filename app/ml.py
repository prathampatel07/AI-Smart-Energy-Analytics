from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


@dataclass
class ForecastResult:
    historical: pd.DataFrame  # columns: timestamp, actual_kwh, predicted_kwh
    future: pd.DataFrame  # columns: timestamp, predicted_kwh
    model_info: Dict[str, object]


def _make_time_features(ts: pd.Series) -> pd.DataFrame:
    dt = pd.to_datetime(ts)
    return pd.DataFrame(
        {
            "hour": dt.dt.hour.astype(int),
            "dayofweek": dt.dt.dayofweek.astype(int),
            "month": dt.dt.month.astype(int),
            "day": dt.dt.day.astype(int),
            "is_weekend": (dt.dt.dayofweek >= 5).astype(int),
        }
    )


def _add_lag_features(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    out = df.copy()
    out["lag_1"] = out[value_col].shift(1)
    out["lag_24"] = out[value_col].shift(24)
    out["roll_24_mean"] = out[value_col].shift(1).rolling(24, min_periods=6).mean()
    return out


def _prepare_training_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[["timestamp", "energy_kwh"]].copy()
    df = df.sort_values("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = _add_lag_features(df, "energy_kwh")
    tf = _make_time_features(df["timestamp"])
    df = pd.concat([df, tf], axis=1)
    df = df.dropna()
    return df


def train_and_forecast_for_building(
    facts: pd.DataFrame,
    building_id: str,
    horizon_hours: int,
    freq: str = "h",
) -> ForecastResult:
    """
    Trains one model per building (scales across buildings via building partitioning).
    Uses calendar + lag features; forecasts future values iteratively.
    """
    bdf = facts[facts["building_id"].astype(str) == str(building_id)].copy()
    bdf = bdf.dropna(subset=["timestamp", "energy_kwh"])
    if bdf.empty:
        raise ValueError("No data for building_id")

    bdf["timestamp"] = pd.to_datetime(bdf["timestamp"], errors="coerce")
    bdf["energy_kwh"] = pd.to_numeric(bdf["energy_kwh"], errors="coerce")
    bdf = bdf.dropna(subset=["timestamp", "energy_kwh"]).sort_values("timestamp")

    train_df = _prepare_training_frame(bdf)
    if len(train_df) < 72:
        raise ValueError("Need at least ~72 hourly points (3 days) after lagging to model reliably.")

    feature_cols = ["lag_1", "lag_24", "roll_24_mean", "hour", "dayofweek", "month", "day", "is_weekend"]
    X = train_df[feature_cols].to_numpy()
    y = train_df["energy_kwh"].to_numpy()

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
        min_samples_leaf=2,
    )
    model.fit(X, y)

    # Historical in-sample predictions (for visualization + inefficiency scoring)
    hist_pred = model.predict(X)
    historical = train_df[["timestamp", "energy_kwh"]].rename(columns={"energy_kwh": "actual_kwh"})
    historical["predicted_kwh"] = hist_pred

    # Future forecasting (recursive with predicted values)
    last_ts = bdf["timestamp"].max()
    future_index = pd.date_range(start=last_ts + pd.Timedelta(hours=1), periods=int(horizon_hours), freq=freq)
    series = bdf.set_index("timestamp")["energy_kwh"].astype(float).sort_index()
    series = series[~series.index.duplicated(keep="last")]

    preds = []
    all_values = series.copy()

    for ts in future_index:
        lag_1 = float(all_values.iloc[-1]) if len(all_values) >= 1 else np.nan
        lag_24 = float(all_values.iloc[-24]) if len(all_values) >= 24 else np.nan
        roll_24_mean = float(all_values.tail(24).mean()) if len(all_values) >= 6 else np.nan

        tf = _make_time_features(pd.Series([ts]))
        row = pd.DataFrame(
            {
                "lag_1": [lag_1],
                "lag_24": [lag_24],
                "roll_24_mean": [roll_24_mean],
                "hour": tf["hour"].iloc[0],
                "dayofweek": tf["dayofweek"].iloc[0],
                "month": tf["month"].iloc[0],
                "day": tf["day"].iloc[0],
                "is_weekend": tf["is_weekend"].iloc[0],
            }
        )
        row = row.fillna(method="ffill", axis=0).fillna(all_values.mean() if len(all_values) else 0.0)

        pred = float(model.predict(row[feature_cols].to_numpy())[0])
        pred = max(pred, 0.0)
        preds.append(pred)
        all_values.loc[ts] = pred

    future = pd.DataFrame({"timestamp": future_index, "predicted_kwh": preds})

    return ForecastResult(
        historical=historical.reset_index(drop=True),
        future=future.reset_index(drop=True),
        model_info={
            "building_id": str(building_id),
            "trained_points": int(len(train_df)),
            "horizon_hours": int(horizon_hours),
            "feature_cols": feature_cols,
            "model": "RandomForestRegressor",
        },
    )

