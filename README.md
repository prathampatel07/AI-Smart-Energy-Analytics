# Energy Analytics (Flask + scikit-learn)

Scalable energy analytics system for **multiple buildings**:
- Ingest **time-series** energy data (CSV)
- Produce **historical predictions** and **future forecasts**
- Convert predictions into **cost-based insights** (tariff-aware)
- Detect **inefficiencies/anomalies** and generate **actionable recommendations**
- Visualize everything in an **interactive dashboard**

## CSV format

Your uploaded CSV must include:
- `timestamp` (ISO format recommended, e.g. `2026-04-01 13:00:00`)
- `building_id` (string or int)
- `energy_kwh` (numeric)

Example:

```csv
timestamp,building_id,energy_kwh
2026-04-01 00:00:00,B001,42.1
2026-04-01 01:00:00,B001,40.7
```

## Run locally (Windows / PowerShell)

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Generate sample data

```powershell
python scripts\generate_sample_data.py --out data\sample_energy.csv
```

Then upload `data\sample_energy.csv` in the UI.

## Unified fact table (concept)

The system builds a unified “fact” table in memory for analysis and visualization:
- `building_id`
- `timestamp`
- `actual_kwh` (historical only)
- `predicted_kwh` (historical + future)
- `is_future` (boolean)
- `rate_per_kwh`
- `actual_cost`, `predicted_cost`, `cost_delta`
- `inefficiency_flag` + `inefficiency_reason`

This structure supports historical backtesting and future forecasting consistently.
