const CHART_TEXT = "#94a3b8"; // slate-400
const CHART_GRID = "rgba(255, 255, 255, 0.08)";

function fmtINR(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(x);
}

/** Plain number for elements that already show ₹ via CSS */
function fmtINRPlain(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(x);
}

function fmtNum(x, digits = 2) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(x);
}

async function fetchJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) {
    const msg = data && data.error ? data.error : "Request failed";
    throw new Error(msg);
  }
  return data;
}

let energyChart = null;
let costChart = null;
let savingsDonutChart = null;
let ineffGaugeChart = null;

function chartDefaults() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.color = CHART_TEXT;
  Chart.defaults.borderColor = CHART_GRID;
  Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
}

function setTopKpis(summary) {
  const elCur = document.getElementById("kpiCurrentKwh");
  const elPred = document.getElementById("kpiPredictedKwh");
  const elFut = document.getElementById("kpiFutureCost");
  const elAcc = document.getElementById("kpiAccuracy");
  if (elCur) elCur.textContent = fmtNum(summary.historical_actual_kwh, 1);
  if (elPred) elPred.textContent = fmtNum(summary.historical_predicted_kwh, 1);
  if (elFut) elFut.textContent = summary.future_predicted_cost != null ? fmtINRPlain(summary.future_predicted_cost) : "—";
  
  if (elAcc) {
    const a = Number(summary.historical_actual_kwh);
    const p = Number(summary.historical_predicted_kwh);
    if (a && p) {
      const err = Math.abs(a - p) / Math.max(a, p);
      elAcc.textContent = Math.round((1 - err) * 100).toString();
    } else {
      elAcc.textContent = "—";
    }
  }
}

function setCostStrip(factRows, rate) {
  const hist = factRows.filter((r) => !r.is_future);
  let sumActualCost = 0;
  let sumPredCost = 0;
  let waste = 0;
  for (const r of hist) {
    const ac = Number(r.actual_cost);
    const pc = Number(r.predicted_cost);
    const cd = Number(r.cost_delta);
    if (!Number.isNaN(ac)) sumActualCost += ac;
    if (!Number.isNaN(pc)) sumPredCost += pc;
    if (!Number.isNaN(cd) && cd > 0) waste += cd;
  }
  const elC = document.getElementById("costCurrent");
  const elP = document.getElementById("costPredictedHist");
  const elT = document.getElementById("costTotalActual");
  const elS = document.getElementById("potentialSavings");
  if (elC) elC.textContent = fmtINRPlain(sumActualCost);
  if (elP) elP.textContent = fmtINRPlain(sumPredCost);
  if (elT) elT.textContent = fmtINRPlain(sumActualCost);
  if (elS) elS.textContent = fmtINRPlain(waste > 0 ? waste : 0);
}

function setAlerts(recs, ineffCount) {
  const box = document.getElementById("alertsBox");
  const alertBadge = document.getElementById("activeAlertsCount");
  
  const totalAlerts = (recs || []).length + (ineffCount > 0 ? 1 : 0);
  if (alertBadge) alertBadge.textContent = totalAlerts.toString();
  
  if (!box) return;
  box.innerHTML = "";
  const items = (recs || []).slice(0, 5);
  if (!items.length && !ineffCount) {
    box.innerHTML = `<p class="placeholder-text mb-0">No active alerts.</p>`;
    return;
  }
  for (const r of items) {
    const div = document.createElement("div");
    div.className = "energy-alert-item";
    div.innerHTML = `<span class="icon" aria-hidden="true">⚠</span><span>${escapeHtml(r.title)}: ${escapeHtml(r.detail)}</span>`;
    box.appendChild(div);
  }
  if (ineffCount > 0) {
    const div = document.createElement("div");
    div.className = "energy-alert-item";
    div.innerHTML = `<span class="icon" aria-hidden="true">●</span><span>${ineffCount} timestamp(s) flagged as inefficient.</span>`;
    box.appendChild(div);
  }
}

function escapeHtml(s) {
  const t = document.createElement("div");
  t.textContent = s;
  return t.innerHTML;
}

function setSummary(summary, modelInfo) {
  const badge = document.getElementById("modelBadge");
  if (badge) badge.textContent = modelInfo?.model || "RF";

  setTopKpis(summary);

  const box = document.getElementById("summaryBox");
  if (!box) return;
  box.innerHTML = "";
  const items = [
    ["Historical points", summary.historical_points],
    ["Inefficiencies flagged", summary.inefficiency_count],
    ["Historical cost delta (Σ)", summary.historical_cost_delta_total, true],
    ["Future predicted (kWh)", summary.future_predicted_kwh],
  ];
  for (const row of items) {
    const [label, value, money] = row;
    const el = document.createElement("div");
    el.className = "energy-summary-item";
    el.innerHTML = `<span class="lbl">${label}</span><span class="val">${money ? fmtINR(value) : fmtNum(value)}</span>`;
    box.appendChild(el);
  }
}

function setRecs(recs) {
  const box = document.getElementById("recsBox");
  if (!box) return;
  box.innerHTML = "";
  const list = recs || [];
  if (!list.length) {
    box.innerHTML = `<p class="energy-placeholder small mb-0">No recommendations.</p>`;
    return;
  }
  const icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>`;
  for (const r of list) {
    const el = document.createElement("div");
    el.className = "energy-rec-item";
    el.innerHTML = `${icon}<div><div class="energy-rec-title">${escapeHtml(r.title)}</div><div class="energy-rec-detail">${escapeHtml(r.detail)}</div></div>`;
    box.appendChild(el);
  }
}

function setFlagsTable(rows) {
  const body = document.getElementById("flagsTable");
  if (!body) return;
  body.innerHTML = "";
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="5" class="text-energy-muted">No inefficiencies flagged.</td></tr>`;
    return;
  }
  for (const r of rows.slice(0, 12)) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="badge rounded-pill" style="background:rgba(0,229,255,.12);color:#00e5ff;border:1px solid rgba(0,229,255,.25);">${escapeHtml(String(r.timestamp))}</span></td>
      <td class="text-end">${fmtNum(r.actual_kwh)}</td>
      <td class="text-end">${fmtNum(r.predicted_kwh)}</td>
      <td class="text-end">${fmtINR(r.cost_delta)}</td>
      <td class="text-energy-muted">${escapeHtml(r.inefficiency_reason || "")}</td>`;
    body.appendChild(tr);
  }
}

function renderDonut(summary) {
  const ctx = document.getElementById("savingsDonutChart");
  const center = document.getElementById("donutCenterLabel");
  if (!ctx) return;
  const sa = Number(summary.historical_actual_kwh);
  const sp = Number(summary.historical_predicted_kwh);
  if (savingsDonutChart) savingsDonutChart.destroy();
  if (!Number.isFinite(sa) || !Number.isFinite(sp) || sa + sp === 0) {
    if (center) center.textContent = "—";
    return;
  }
  const close = Math.min(sa, sp);
  const gap = Math.abs(sa - sp);
  const pct = Math.round((close / Math.max(sa, sp)) * 100);
  if (center) center.textContent = `${pct}%`;

  savingsDonutChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Aligned band", "Deviation"],
      datasets: [
        {
          data: [close, gap],
          backgroundColor: ["rgba(16, 185, 129, 0.8)", "rgba(245, 158, 11, 0.7)"],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => `${c.label}: ${fmtNum(c.parsed)} kWh`,
          },
        },
      },
    },
  });
}

function renderGauge(wasteAmount) {
  const ctx = document.getElementById("ineffGaugeChart");
  const valEl = document.getElementById("ineffGaugeValue");
  if (!ctx) return;
  if (ineffGaugeChart) ineffGaugeChart.destroy();
  const w = Math.max(0, Number(wasteAmount) || 0);
  const cap = Math.max(w * 1.35, 100);
  const rest = Math.max(cap - w, 0);
  if (valEl) valEl.textContent = fmtINRPlain(w);

  ineffGaugeChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [w, rest],
          backgroundColor: ["rgba(239, 68, 68, 0.85)", "rgba(30, 41, 59, 0.9)"],
          borderWidth: 0,
          circumference: 180,
          rotation: 270,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => (c.dataIndex === 0 ? `Exposure: ${fmtINR(w)}` : ""),
          },
        },
      },
    },
  });
}

function renderCharts(factRows) {
  chartDefaults();
  const labels = factRows.map((r) => r.timestamp);
  const actual = factRows.map((r) => (r.is_future ? null : r.actual_kwh));
  const predicted = factRows.map((r) => r.predicted_kwh);
  const isFuture = factRows.map((r) => !!r.is_future);
  const ineff = factRows.map((r) => (r.inefficiency_flag ? r.actual_kwh : null));

  const histBars = factRows.map((r, i) => (!isFuture[i] ? actual[i] : null));
  const futureBars = factRows.map((r, i) => (isFuture[i] ? predicted[i] : null));

  const costDeltas = factRows.map((r) => (r.is_future ? null : r.cost_delta));

  const pointsBadge = document.getElementById("pointsBadge");
  const ineffBadge = document.getElementById("ineffBadge");
  const nFlag = factRows.filter((r) => r.inefficiency_flag).length;
  if (pointsBadge) pointsBadge.textContent = `${factRows.length} pts`;
  if (ineffBadge) ineffBadge.textContent = `${nFlag} flagged`;

  const energyCtx = document.getElementById("energyChart");
  const costCtx = document.getElementById("costChart");

  if (energyChart) energyChart.destroy();
  if (costChart) costChart.destroy();

  if (energyCtx) {
    energyChart = new Chart(energyCtx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            type: "bar",
            label: "Actual (historical)",
            data: histBars,
            backgroundColor: labels.map((_, i) =>
              ineff[i] != null ? "rgba(245, 158, 11, 0.85)" : "rgba(14, 165, 233, 0.65)"
            ),
            borderColor: labels.map((_, i) =>
              ineff[i] != null ? "rgba(245, 158, 11, 1)" : "rgba(14, 165, 233, 1)"
            ),
            borderWidth: 1,
            borderRadius: 4,
            order: 1,
          },
          {
            type: "bar",
            label: "Forecast",
            data: futureBars,
            backgroundColor: "rgba(16, 185, 129, 0.65)",
            borderColor: "rgba(16, 185, 129, 1)",
            borderWidth: 1,
            borderRadius: 4,
            order: 2,
          },
          {
            type: "line",
            label: "Predicted Baseline",
            data: predicted,
            borderColor: "rgba(148, 163, 184, 0.9)",
            backgroundColor: "rgba(148, 163, 184, 0.1)",
            borderWidth: 2,
            tension: 0.25,
            pointRadius: 0,
            yAxisID: "y",
            order: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 12, padding: 16 },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.parsed.y;
                if (v == null) return "";
                return `${ctx.dataset.label}: ${fmtNum(v)} kWh`;
              },
            },
          },
        },
        scales: {
          x: {
            stacked: false,
            ticks: { maxTicksLimit: 12, color: CHART_TEXT },
            grid: { color: CHART_GRID },
          },
          y: {
            stacked: false,
            beginAtZero: true,
            ticks: { color: CHART_TEXT },
            grid: { color: CHART_GRID },
          },
        },
      },
    });
  }

  if (costCtx) {
    costChart = new Chart(costCtx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Δ cost",
            data: costDeltas,
            backgroundColor: costDeltas.map((v) =>
              v == null ? "transparent" : v >= 0 ? "rgba(239, 68, 68, 0.65)" : "rgba(16, 185, 129, 0.65)"
            ),
            borderColor: costDeltas.map((v) =>
              v == null ? "transparent" : v >= 0 ? "rgba(239, 68, 68, 1)" : "rgba(16, 185, 129, 1)"
            ),
            borderWidth: 1,
            borderRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.parsed.y;
                if (v == null) return "";
                return `Δ ${fmtINR(v)}`;
              },
            },
          },
        },
        scales: {
          x: { display: false },
          y: {
            ticks: {
              color: CHART_TEXT,
              callback: (v) => fmtINR(v),
            },
            grid: { color: CHART_GRID },
          },
        },
      },
    });
  }
}

async function populateBuildings() {
  const sel = document.getElementById("buildingSelect");
  if (!sel) return;
  sel.innerHTML = `<option value="">Loading…</option>`;
  const data = await fetchJSON("/api/buildings");
  sel.innerHTML = "";
  if (!data.buildings.length) {
    sel.innerHTML = `<option value="">No buildings — upload CSV</option>`;
    return;
  }
  for (const b of data.buildings) {
    const opt = document.createElement("option");
    opt.value = b;
    opt.textContent = b;
    sel.appendChild(opt);
  }
}

function sumWaste(factRows) {
  let w = 0;
  for (const r of factRows) {
    if (r.is_future) continue;
    const cd = Number(r.cost_delta);
    if (!Number.isNaN(cd) && cd > 0) w += cd;
  }
  return w;
}

async function runAnalysis() {
  const building = document.getElementById("buildingSelect")?.value || "";
  const rate = document.getElementById("rateInput")?.value || "0.15";
  const horizon = document.getElementById("horizonInput")?.value || "48";

  if (!building) {
    alert("Please select a building (upload data if none available).");
    return;
  }

  const btn = document.getElementById("runBtn");
  const refresh = document.getElementById("refreshBtn");
  const prevText = btn?.textContent;
  if (btn) {
    btn.textContent = "Running…";
    btn.disabled = true;
  }
  if (refresh) refresh.disabled = true;

  try {
    const url = `/api/insights?building_id=${encodeURIComponent(building)}&rate_per_kwh=${encodeURIComponent(rate)}&horizon_hours=${encodeURIComponent(horizon)}`;
    const data = await fetchJSON(url);
    setSummary(data.summary, data.model_info);
    setRecs(data.recommendations);
    setAlerts(data.recommendations, data.summary?.inefficiency_count || 0);
    setCostStrip(data.fact_table, Number(rate));
    renderCharts(data.fact_table);
    renderDonut(data.summary);
    renderGauge(sumWaste(data.fact_table));

    const flagged = data.fact_table.filter((r) => !r.is_future && r.inefficiency_flag);
    setFlagsTable(flagged.sort((a, b) => (b.cost_delta || 0) - (a.cost_delta || 0)));
    
    // Update platform status panel
    const bldgDisplay = document.getElementById("statusFacility");
    const syncTime = document.getElementById("lastSyncTime");
    if (bldgDisplay) bldgDisplay.textContent = building;
    if (syncTime) syncTime.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
  } catch (e) {
    alert(e.message || String(e));
  } finally {
    if (btn) {
      btn.textContent = prevText || "Run analysis";
      btn.disabled = false;
    }
    if (refresh) refresh.disabled = false;
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  chartDefaults();
  // We only run this generic setup on Dashboard
  // Other pages handle their own runBtn click events
  const sel = document.getElementById("buildingSelect");
  const runBtn = document.getElementById("runBtn");
  const refresh = document.getElementById("refreshBtn");
  
  if (sel && window.location.pathname.includes('/dashboard')) {
      await populateBuildings();
      runBtn?.addEventListener("click", runAnalysis);
      refresh?.addEventListener("click", async () => {
        await populateBuildings();
      });
      
      const params = new URLSearchParams(window.location.search);
      const bldgId = params.get('building_id');
      if(bldgId) {
          sel.value = bldgId;
          setTimeout(runAnalysis, 100);
      }
  }
});
