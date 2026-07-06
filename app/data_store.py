from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class StorePaths:
    base_dir: Path

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def facts_csv(self) -> Path:
        return self.data_dir / "energy_facts.csv"


def ensure_store(paths: StorePaths) -> None:
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not paths.facts_csv.exists():
        pd.DataFrame(columns=["timestamp", "building_id", "energy_kwh"]).to_csv(paths.facts_csv, index=False)


def load_facts(paths: StorePaths) -> pd.DataFrame:
    ensure_store(paths)
    df = pd.read_csv(paths.facts_csv)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    df = df.dropna(subset=["timestamp", "building_id", "energy_kwh"])
    df["energy_kwh"] = pd.to_numeric(df["energy_kwh"], errors="coerce")
    df = df.dropna(subset=["energy_kwh"])
    df["building_id"] = df["building_id"].astype(str)
    return df


def append_facts(paths: StorePaths, new_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Append new time-series rows into a single scalable fact-store CSV.
    De-duplicates by (building_id, timestamp) keeping last.
    """
    ensure_store(paths)
    existing = load_facts(paths)
    if existing.empty:
        combined = new_rows.copy()
    else:
        combined = pd.concat([existing, new_rows], ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], errors="coerce", utc=False)
    combined = combined.dropna(subset=["timestamp", "building_id", "energy_kwh"])
    combined["energy_kwh"] = pd.to_numeric(combined["energy_kwh"], errors="coerce")
    combined = combined.dropna(subset=["energy_kwh"])
    combined["building_id"] = combined["building_id"].astype(str)
    combined = combined.sort_values(["building_id", "timestamp"])
    combined = combined.drop_duplicates(subset=["building_id", "timestamp"], keep="last")
    combined.to_csv(paths.facts_csv, index=False)
    return combined

