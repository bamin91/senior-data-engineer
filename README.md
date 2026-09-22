# Senior Data Engineer Case Study: Execution Guide

This repository contains a high-reliability telemetry ingestion pipeline Proof-of-Concept (POC) and an interactive visualization dashboard designed to support Vattenfall's BA Markets data consumers. 

* For architectural details and tradeoffs, please refer to `RFC.md`.
* For directory mapping and file locations, please see `PROJECT_LAYOUT.md`.
* For the raw SQL queries and their compiled output tables, please see `reporting_queries.sql` and `QUERY_OUTPUTS.md`.

---

## Environment Setup

Ensure you have Git and Python 3.10+ installed on your local machine.

### macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell / Git Bash):
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

---

## How to Run the POC Pipeline & Analytics Dashboard

Execute the following three steps in parallel terminal sessions with your virtual environment (`.venv`) activated:

### 1. Start the Telemetry Source Simulator
This launches the underlying field SCADA mock service.
```bash
uvicorn app.main:app --reload
```

### 2. Launch the Ingestion & Seeding Engine
This initializes the one-shot 5-day historical seed and enters an ongoing live stream polling loop.
```bash
python app/pipeline_orchestrator.py
```

### 3. Launch the Interactive Visualization Dashboard
This opens a browser window displaying visual analytics on top of the reporting queries.
```bash
streamlit run app/dashboard.py
```
