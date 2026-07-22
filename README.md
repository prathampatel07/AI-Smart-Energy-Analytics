# Smart Energy Analytics Platform

 **Live Demo:**  
 https://ai-smart-energy-analytics.onrender.com

*This application is deployed on Railway and can be accessed directly through the link above. No local installation is required to explore the platform.*

---

##  Overview

Smart Energy Analytics Platform is an enterprise-grade AI-powered web application designed to help organizations monitor, analyze, and optimize energy consumption across multiple facilities. The platform enables users to upload energy datasets, generate machine learning-based consumption forecasts, detect anomalies, identify energy losses, estimate operational costs, and receive intelligent optimization recommendations through an interactive analytics dashboard. Built using Flask, Scikit-learn, Pandas, and modern frontend technologies, the platform provides a scalable and production-ready solution inspired by commercial energy management systems such as Siemens Energy, Schneider Electric, ABB, and Microsoft Azure.

---

##  Key Features

- **Enterprise Dashboard:** Executive command center for real-time overview.
- **AI-powered Energy Forecasting:** Machine learning baselines and future projections.
- **CSV Data Upload & Validation:** Secure data ingestion pipeline.
- **Energy Consumption Analytics:** Aggregated insights across multiple facilities.
- **Cost Optimization:** Translates energy deviations into actionable financial metrics.
- **Anomaly Detection:** Flags inefficiencies and abnormal consumption spikes.
- **AI Recommendations:** Generates actionable steps to mitigate energy waste.
- **Multi-Facility Monitoring:** Scale across thousands of buildings simultaneously.
- **Interactive Charts & KPIs:** Professional data visualization using Chart.js.
- **Reports & Insights:** Exportable operational summaries.
- **Responsive Enterprise UI:** Modern, accessible, and polished B2B SaaS interface.
- **Railway Cloud Deployment:** Containerized and production-ready.

---

##  Technology Stack

**Frontend**
- HTML5
- CSS3
- JavaScript
- Chart.js

**Backend**
- Flask
- Python

**Machine Learning**
- Scikit-learn
- Pandas
- NumPy

**Deployment**
- Railway
- GitHub

---

##  Project Workflow

```text
CSV Upload
    ↓
Data Validation
    ↓
Data Processing
    ↓
Machine Learning Forecasting
    ↓
Energy Analysis
    ↓
Cost Optimization
    ↓
AI Recommendations
    ↓
Interactive Dashboard
```

---

##  Quick Start

### Using the Live Environment
1. Open the **Live Demo** using the Railway link above.
2. Upload a sample CSV dataset.
3. Select a building/facility.
4. Run the analysis.
5. Explore forecasts, analytics, recommendations, and reports.

### Running Locally (Windows / PowerShell)

1. **Set up virtual environment & install dependencies:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **Start the Flask server:**
   ```powershell
   python run.py
   ```
3. Open `http://127.0.0.1:5000` in your browser.

4. **Generate Sample Data (Optional):**
   ```powershell
   python scripts\generate_sample_data.py --out data\sample_energy.csv
   ```
   Then upload `data\sample_energy.csv` in the UI to explore the platform.

---

##  Data Schema & Architecture

### CSV Upload Format
Your uploaded CSV must include the following schema:
- `timestamp` (ISO format recommended, e.g. `2026-04-01 13:00:00`)
- `building_id` (string or int)
- `energy_kwh` (numeric)

**Example:**
```csv
timestamp,building_id,energy_kwh
2026-04-01 00:00:00,B001,42.1
2026-04-01 01:00:00,B001,40.7
```
*(Note: Optional columns like `tariff` or `temperature` will be preserved in the data warehouse.)*

### Unified Fact Table (Concept)
The system builds a unified "fact" table in memory for analysis and visualization:
- `building_id`
- `timestamp`
- `actual_kwh` (historical only)
- `predicted_kwh` (historical + future)
- `is_future` (boolean)
- `rate_per_kwh`
- `actual_cost`, `predicted_cost`, `cost_delta`
- `inefficiency_flag` + `inefficiency_reason`

This structure supports historical backtesting and future forecasting consistently across all backend modules.

---

##  Future Enhancements

- IoT Sensor Integration
- Real-time Monitoring
- Predictive Maintenance
- User Authentication
- Weather API Integration
- Multi-Tenant Support
- Advanced Reporting
