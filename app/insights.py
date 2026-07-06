from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class InsightBundle:
    fact_table: pd.DataFrame
    summary: Dict[str, object]
    recommendations: List[Dict[str, str]]


def build_unified_fact_table(
    building_id: str,
    historical: pd.DataFrame,
    future: pd.DataFrame,
    rate_per_kwh: float,
) -> pd.DataFrame:
    """
    Unified fact table:
      - historical rows have actual + predicted
      - future rows have predicted only
    """
    rate = float(rate_per_kwh)
    hist = historical.copy()
    hist["building_id"] = str(building_id)
    hist["is_future"] = False
    hist["actual_kwh"] = pd.to_numeric(hist["actual_kwh"], errors="coerce")
    hist["predicted_kwh"] = pd.to_numeric(hist["predicted_kwh"], errors="coerce")
    hist["rate_per_kwh"] = rate
    hist["actual_cost"] = hist["actual_kwh"] * rate
    hist["predicted_cost"] = hist["predicted_kwh"] * rate
    hist["cost_delta"] = hist["actual_cost"] - hist["predicted_cost"]

    fut = future.copy()
    fut["building_id"] = str(building_id)
    fut["is_future"] = True
    fut["actual_kwh"] = np.nan
    fut["rate_per_kwh"] = rate
    fut["actual_cost"] = np.nan
    fut["predicted_cost"] = fut["predicted_kwh"] * rate
    fut["cost_delta"] = np.nan

    fact = pd.concat([hist, fut], ignore_index=True)
    fact["timestamp"] = pd.to_datetime(fact["timestamp"])
    fact = fact.sort_values("timestamp").reset_index(drop=True)
    return fact[
        [
            "building_id",
            "timestamp",
            "is_future",
            "actual_kwh",
            "predicted_kwh",
            "rate_per_kwh",
            "actual_cost",
            "predicted_cost",
            "cost_delta",
        ]
    ]


def detect_inefficiencies(fact_table: pd.DataFrame) -> pd.DataFrame:
    """
    Flags historical points where actual significantly exceeds predicted.
    Simple, explainable rules to keep it production-friendly.
    """
    df = fact_table.copy()
    df["inefficiency_flag"] = False
    df["inefficiency_reason"] = ""

    hist = df[~df["is_future"]].copy()
    if hist.empty:
        return df

    err = (hist["actual_kwh"] - hist["predicted_kwh"]).astype(float)
    abs_err = err.abs()
    robust_scale = float(abs_err.median() + 1e-6)
    pct = (err / (hist["predicted_kwh"].abs() + 1e-6)).astype(float)

    # A point is inefficient if it's both large in absolute terms and significant in relative terms.
    flag = (err > (3.0 * robust_scale)) & (pct > 0.20)

    # Also flag persistent night-time baseload spikes (suggests HVAC/lighting left on)
    hour = pd.to_datetime(hist["timestamp"]).dt.hour
    night = hour.isin([0, 1, 2, 3, 4, 5])
    night_flag = night & (pct > 0.25) & (err > (2.0 * robust_scale))

    flagged_idx = hist.index[flag | night_flag]
    df.loc[flagged_idx, "inefficiency_flag"] = True
    df.loc[flagged_idx, "inefficiency_reason"] = np.where(
        night.loc[flagged_idx],
        "Night-time usage spike vs expected baseline",
        "Actual usage significantly above forecast",
    )
    return df


def recommend_actions(flagged_fact: pd.DataFrame) -> List[Dict[str, str]]:
    hist_flags = flagged_fact[(~flagged_fact["is_future"]) & (flagged_fact["inefficiency_flag"])].copy()
    if hist_flags.empty:
        return [
            {
                "title": "No major inefficiencies detected",
                "detail": "Usage aligns with forecast; consider tightening tariff assumptions or adding sub-metering for deeper optimization.",
            }
        ]

    hist_flags["hour"] = pd.to_datetime(hist_flags["timestamp"]).dt.hour
    night = hist_flags[hist_flags["hour"].isin([0, 1, 2, 3, 4, 5])]
    day = hist_flags[~hist_flags["hour"].isin([0, 1, 2, 3, 4, 5])]

    recs: List[Dict[str, str]] = []

    if len(night) >= 3:
        recs.append(
            {
                "title": "Reduce night-time baseload",
                "detail": "Repeated overnight spikes suggest HVAC, lighting, or plug loads are left running. Add/verify schedules and after-hours shutdown policies.",
            }
        )

    if len(day) >= 3:
        recs.append(
            {
                "title": "Investigate peak-hour drivers",
                "detail": "Daytime usage exceeds expected profile. Check HVAC setpoints, equipment runtime, and occupancy-driven loads; consider demand response or staggered start strategies.",
            }
        )

    top_delta = hist_flags.nlargest(5, "cost_delta")[["timestamp", "cost_delta"]]
    worst = ", ".join([f"{t:%Y-%m-%d %H:%M} (+{d:.2f})" for t, d in zip(top_delta["timestamp"], top_delta["cost_delta"])])
    recs.append(
        {
            "title": "Prioritize the most expensive deviations",
            "detail": f"Start with these timestamps where overspend vs forecast was highest: {worst}",
        }
    )
    return recs


def summarize(fact_table: pd.DataFrame) -> Dict[str, object]:
    hist = fact_table[~fact_table["is_future"]].copy()
    fut = fact_table[fact_table["is_future"]].copy()

    out: Dict[str, object] = {
        "historical_points": int(len(hist)),
        "future_points": int(len(fut)),
        "rate_per_kwh": float(fact_table["rate_per_kwh"].iloc[0]) if len(fact_table) else None,
    }

    if len(hist):
        out.update(
            {
                "historical_actual_kwh": float(hist["actual_kwh"].sum()),
                "historical_predicted_kwh": float(hist["predicted_kwh"].sum()),
                "historical_cost_delta_total": float(hist["cost_delta"].sum()),
                "inefficiency_count": int(hist.get("inefficiency_flag", pd.Series(False)).sum()),
            }
        )

    if len(fut):
        out.update(
            {
                "future_predicted_kwh": float(fut["predicted_kwh"].sum()),
                "future_predicted_cost": float(fut["predicted_cost"].sum()),
            }
        )
    return out


def build_insights(building_id: str, historical: pd.DataFrame, future: pd.DataFrame, rate_per_kwh: float) -> InsightBundle:
    fact = build_unified_fact_table(building_id, historical, future, rate_per_kwh)
    fact = detect_inefficiencies(fact)
    recs = recommend_actions(fact)
    return InsightBundle(
        fact_table=fact,
        summary=summarize(fact),
        recommendations=recs,
    )

