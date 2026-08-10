# Repository Directory Layout Mapping

```text
vattenfall-hiring-data-engineer/
│
├── app/
│   ├── __init__.py                # Packages initialization marker
│   ├── assets.py                  # Static Fleet Registry Dimension Source
│   ├── dashboard.py               # Streamlit Visual KPI Dashboard Engine
│   ├── generator.py               # SCADA Telemetry Stream Simulator
│   ├── main.py                    # Core FastAPI Application Server Entry
│   └── pipeline_orchestrator.py   # Python Ingestion Engine & Self-Healing Pipeline
│
├── docs/                          # Project Documentation & Artifacts
│   └── Vattenfall_Renewable_Energy_Fleet_Dashboard.pdf
│
├── .gitignore                     # Git Tracking Isolation Exclusions
├── PROJECT_LAYOUT.md              # Structural Repository Guide Map
├── QUERY_OUTPUTS.md               # Compiled SQL Queries with Markdown Output Tables
├── requirements.txt               # Unified Workspace Library Dependencies
├── RFC.md                         # Comprehensive High-Reliability Architecture RFC
└── reporting_queries.sql          # 5 Core Production Business Analytics Queries
```