import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = "vattenfall_lakehouse.db"

st.set_page_config(page_title="Vattenfall Renewable Energy Fleet Dashboard", layout="wide")
st.title("⚡ Vattenfall BA Markets — Fleet Analytics Dashboard")
st.markdown("Proof-of-Concept visualization tracking core telemetry KPIs.")

if not os.path.exists(DB_PATH):
    st.error(f"Database file '{DB_PATH}' not found. Please run the pipeline orchestrator first to seed the tables.")
else:
    conn = sqlite3.connect(DB_PATH)
    
    # KPI 1: Capacity Factor Per Asset Per Day
    st.header("1. Daily Capacity Factor per Asset")
    q1 = """
    SELECT t.asset_id, DATE(t.timestamp) AS date,
           ROUND(SUM(t.power_output_kw) / (a.rated_capacity_kw * COUNT(t.id)) * 100, 2) AS capacity_factor_pct
    FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
    GROUP BY t.asset_id, date ORDER BY date DESC;
    """
    df1 = pd.read_sql_query(q1, conn)
    st.dataframe(df1, use_container_width=True)
    
    # KPI 2: Fleet Availability % by Site/Country
    st.header("2. Fleet Availability % by Site & Country")
    q2 = """
    SELECT a.site, a.country,
           ROUND(SUM(CASE WHEN t.status_code IN ('OK', 'CURTAILED') THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id), 2) AS availability_pct
    FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
    GROUP BY a.site, a.country;
    """
    df2 = pd.read_sql_query(q2, conn)
    st.bar_chart(data=df2, x="site", y="availability_pct", color="country")
    
    # KPI 3 & 4: Fault Frequency Breakdown & Top Bottlenecks
    col1, col2 = st.columns(2)
    with col1:
        st.header("3. Top 5 Worst-Performing Assets (Downtime)")
        q3 = """
        SELECT t.asset_id, COUNT(CASE WHEN t.status_code IN ('FAULT', 'OFFLINE') THEN 1 END) AS downtime_records
        FROM fact_telemetry_silver t GROUP BY t.asset_id ORDER BY downtime_records DESC LIMIT 5;
        """
        df3 = pd.read_sql_query(q3, conn)
        st.dataframe(df3, use_container_width=True)
        
    with col2:
        st.header("4. Fault Code Frequency Breakdown")
        q4 = """
        SELECT t.fault_code, COUNT(t.id) AS occurrences
        FROM fact_telemetry_silver t WHERE t.status_code = 'FAULT' AND t.fault_code IS NOT NULL
        GROUP BY t.fault_code ORDER BY occurrences DESC;
        """
        df4 = pd.read_sql_query(q4, conn)
        st.dataframe(df4, use_container_width=True)
        
    # KPI 5: Daily Generation Comparison (Wind vs Solar)
    st.header("5. Daily Generation Comparison: Wind vs. Solar (MWh)")
    q5 = """
    SELECT a.country, DATE(t.timestamp) AS date,
           ROUND(SUM(CASE WHEN a.type = 'wind' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS wind_mwh,
           ROUND(SUM(CASE WHEN a.type = 'solar' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS solar_mwh
    FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
    GROUP BY a.country, date ORDER BY date DESC;
    """
    df5 = pd.read_sql_query(q5, conn)
    st.dataframe(df5, use_container_width=True)
    
    conn.close()
