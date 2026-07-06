from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for
import csv
from io import StringIO

from .data_store import StorePaths, append_facts, load_facts
from .insights import build_insights
from .ml import train_and_forecast_for_building
from .settings_manager import load_settings, save_settings

bp = Blueprint("routes", __name__)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _paths() -> StorePaths:
    return StorePaths(base_dir=_project_root())


def _safe_float(value: str, default: float) -> float:
    try:
        if not value: return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: str, default: int) -> int:
    try:
        if not value: return default
        return int(value)
    except Exception:
        return default


def _json_safe_records(df: pd.DataFrame) -> list[dict]:
    safe = df.replace([np.inf, -np.inf], np.nan).astype(object)
    safe = safe.where(pd.notnull(safe), None)
    return safe.to_dict(orient="records")


@bp.get("/")
def index():
    return send_from_directory(current_app.static_folder, "energy-landing.html")


@bp.get("/landing")
def cinematic_landing():
    return send_from_directory(current_app.static_folder, "energy-landing.html")


@bp.get("/upload")
def upload_page():
    return render_template("upload.html", settings=load_settings())


@bp.post("/upload")
def upload_csv():
    file = request.files.get("file")
    if not file or not file.filename:
        return render_template("upload.html", error="Please choose a CSV file.", settings=load_settings()), 400

    filename = file.filename.lower()
    if not filename.endswith(".csv"):
        return render_template("upload.html", error="Only .csv files are supported.", settings=load_settings()), 400

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return render_template("upload.html", error=f"Could not read CSV: {e}", settings=load_settings()), 400

    required = {"timestamp", "building_id", "energy_kwh"}
    missing = required - set(df.columns)
    if missing:
        return render_template(
            "upload.html",
            error=f"Missing required columns: {', '.join(sorted(missing))}",
            settings=load_settings()
        ), 400

    df = df[list(required)].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    df["energy_kwh"] = pd.to_numeric(df["energy_kwh"], errors="coerce")
    df["building_id"] = df["building_id"].astype(str)
    df = df.dropna(subset=["timestamp", "building_id", "energy_kwh"])

    if df.empty:
        return render_template("upload.html", error="No valid rows found after parsing.", settings=load_settings()), 400

    append_facts(_paths(), df)
    return redirect(url_for("routes.dashboard", uploaded="1"))


@bp.get("/dashboard")
def dashboard():
    uploaded = request.args.get("uploaded") == "1"
    settings = load_settings()
    preselect_building = request.args.get("building_id", "")
    return render_template("dashboard.html", uploaded=uploaded, settings=settings, preselect_building=preselect_building)


@bp.get("/analytics")
def analytics():
    facts = load_facts(_paths())
    settings = load_settings()
    
    if facts.empty:
        return render_template("analytics.html", has_data=False, settings=settings)
        
    # Aggregate data for analytics
    building_totals = facts.groupby("building_id")["energy_kwh"].sum().reset_index()
    building_totals = building_totals.sort_values("energy_kwh", ascending=False)
    
    facts["hour"] = facts["timestamp"].dt.hour
    hourly_avg = facts.groupby("hour")["energy_kwh"].mean().reset_index()
    
    return render_template("analytics.html", 
                          has_data=True, 
                          settings=settings,
                          building_totals=_json_safe_records(building_totals),
                          hourly_avg=_json_safe_records(hourly_avg),
                          total_buildings=facts["building_id"].nunique(),
                          total_kwh=facts["energy_kwh"].sum())

@bp.get("/forecasting")
def forecasting():
    settings = load_settings()
    preselect_building = request.args.get("building_id", "")
    return render_template("forecasting.html", settings=settings, preselect_building=preselect_building)

@bp.get("/reports")
def reports():
    settings = load_settings()
    facts = load_facts(_paths())
    has_data = not facts.empty
    
    report_data = None
    if has_data:
        total_kwh = facts["energy_kwh"].sum()
        total_cost = total_kwh * settings["tariff_rate"]
        start_date = facts["timestamp"].min().strftime("%Y-%m-%d")
        end_date = facts["timestamp"].max().strftime("%Y-%m-%d")
        bldgs = facts["building_id"].nunique()
        report_data = {
            "total_kwh": total_kwh,
            "total_cost": total_cost,
            "start_date": start_date,
            "end_date": end_date,
            "buildings": bldgs
        }
        
    return render_template("reports.html", settings=settings, has_data=has_data, report_data=report_data)

@bp.get("/reports/download")
def download_reports():
    facts = load_facts(_paths())
    if facts.empty:
        return "No data", 400
        
    facts["date"] = facts["timestamp"].dt.date
    daily = facts.groupby(["date", "building_id"])["energy_kwh"].sum().reset_index()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Building ID", "Total Energy (kWh)"])
    for _, row in daily.iterrows():
        writer.writerow([row["date"], row["building_id"], row["energy_kwh"]])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=energy_report.csv"}
    )

@bp.get("/facilities")
def facilities():
    settings = load_settings()
    facts = load_facts(_paths())
    
    if facts.empty:
         return render_template("facilities.html", has_data=False, settings=settings, facilities=[])
         
    bldg_stats = []
    for b_id, group in facts.groupby("building_id"):
        total_kwh = group["energy_kwh"].sum()
        avg_kwh = group["energy_kwh"].mean()
        last_kwh = group.sort_values("timestamp").iloc[-1]["energy_kwh"]
        
        health = "Good"
        health_color = "success"
        if last_kwh > avg_kwh * 1.5:
             health = "Warning"
             health_color = "warning"
        elif last_kwh > avg_kwh * 2.0:
             health = "Critical"
             health_color = "danger"
             
        bldg_stats.append({
             "building_id": b_id,
             "total_kwh": total_kwh,
             "avg_kwh": avg_kwh,
             "last_kwh": last_kwh,
             "total_cost": total_kwh * settings["tariff_rate"],
             "health": health,
             "health_color": health_color,
             "reading_count": len(group)
        })
        
    return render_template("facilities.html", has_data=True, settings=settings, facilities=bldg_stats)

@bp.get("/ai-recommendations")
def ai_recommendations():
    settings = load_settings()
    facts = load_facts(_paths())
    has_data = not facts.empty
    preselect_building = request.args.get("building_id", "")
    return render_template("ai_recommendations.html", settings=settings, has_data=has_data, preselect_building=preselect_building)

@bp.get("/cost-optimization")
def cost_optimization():
    settings = load_settings()
    preselect_building = request.args.get("building_id", "")
    return render_template("cost_optimization.html", settings=settings, preselect_building=preselect_building)

@bp.route("/settings", methods=["GET", "POST"])
def settings_page():
    current = load_settings()
    if request.method == "POST":
        current["tariff_rate"] = _safe_float(request.form.get("tariff_rate"), 0.15)
        current["forecast_horizon"] = _safe_int(request.form.get("forecast_horizon"), 48)
        current["currency"] = request.form.get("currency", "INR")
        current["org_name"] = request.form.get("org_name", "Acme Energy Corp")
        current["timezone"] = request.form.get("timezone", "UTC")
        save_settings(current)
        return redirect(url_for("routes.settings_page", saved="1"))
        
    saved = request.args.get("saved") == "1"
    return render_template("settings.html", settings=current, saved=saved)

@bp.get("/api/buildings")
def api_buildings():
    facts = load_facts(_paths())
    buildings = sorted(facts["building_id"].astype(str).unique().tolist()) if not facts.empty else []
    return jsonify({"buildings": buildings})

@bp.get("/api/insights")
def api_insights():
    settings = load_settings()
    building_id = request.args.get("building_id", "").strip()
    rate = _safe_float(request.args.get("rate_per_kwh", ""), settings.get("tariff_rate", 0.15))
    horizon = _safe_int(request.args.get("horizon_hours", ""), settings.get("forecast_horizon", 48))

    if not building_id:
        return jsonify({"error": "building_id is required"}), 400
    horizon = max(1, min(horizon, 24 * 14))
    rate = max(0.0, min(rate, 10.0))

    facts = load_facts(_paths())
    try:
        fc = train_and_forecast_for_building(facts, building_id=building_id, horizon_hours=horizon)
        bundle = build_insights(building_id, fc.historical, fc.future, rate_per_kwh=rate)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    fact = bundle.fact_table.copy()
    fact["timestamp"] = pd.to_datetime(fact["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(
        {
            "model_info": fc.model_info,
            "summary": bundle.summary,
            "recommendations": bundle.recommendations,
            "fact_table": _json_safe_records(fact),
        }
    )
