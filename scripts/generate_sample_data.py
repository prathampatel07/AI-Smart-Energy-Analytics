from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class BuildingProfile:
    building_id: str
    base: float
    daily_amp: float
    weekend_drop: float
    noise: float


def synthesize(
    buildings: list[BuildingProfile], start: str, days: int, freq: str, tariff_map: dict[str, float]
) -> pd.DataFrame:
    idx = pd.date_range(start=start, periods=int(days) * 24, freq=freq)
    out = []
    for b in buildings:
        hour = idx.hour.to_numpy()
        dow = idx.dayofweek.to_numpy()
        is_weekend = (dow >= 5).astype(float)

        daily = (np.sin((hour - 7) / 24 * 2 * np.pi) + 1.0) / 2.0  # 0..1
        shape = b.base + b.daily_amp * (0.3 + 0.7 * daily)
        shape = shape * (1.0 - is_weekend * b.weekend_drop)

        # Add a couple of inefficiency events
        spike = np.zeros(len(idx))
        if len(idx) > 200:
            spike[120:128] += b.daily_amp * 0.9
            spike[320:330] += b.daily_amp * 0.6

        y = shape + spike + np.random.normal(0, b.noise, size=len(idx))
        y = np.clip(y, 0, None)
        temperature = np.random.uniform(28.0, 35.0, size=len(idx))
        temperature = np.round(temperature, 1)

        out.append(
            pd.DataFrame(
                {
                    "timestamp": idx,
                    "building_id": b.building_id,
                    "energy_kwh": np.round(y, 3),
                    "tariff": float(tariff_map.get(b.building_id, 0.15)),
                    "temperature": temperature,
                }
            )
        )
    return pd.concat(out, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--start", default="2026-03-01 00:00:00")
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--freq", default="h")
    args = ap.parse_args()

    np.random.seed(42)

    buildings = [
        BuildingProfile("B001", base=22, daily_amp=35, weekend_drop=0.20, noise=1.5),
        BuildingProfile("B002", base=18, daily_amp=22, weekend_drop=0.10, noise=1.2),
        BuildingProfile("B003", base=28, daily_amp=42, weekend_drop=0.25, noise=1.8),
    ]

    tariff_map = {"B001": 0.15, "B002": 0.17, "B003": 0.19}
    df = synthesize(buildings, start=args.start, days=args.days, freq=args.freq, tariff_map=tariff_map)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

