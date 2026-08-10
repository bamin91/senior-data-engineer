-- ============================================================================
-- VATTENFALL DATA ENGINEER CASE STUDY — CORE ANALYTICAL REPORTING LAYER
-- ============================================================================

-- 1. Daily Capacity Factor per Asset
SELECT 
    t.asset_id,
    DATE(t.timestamp) AS date,
    ROUND(SUM(t.power_output_kw) / (a.rated_capacity_kw * COUNT(t.id)) * 100, 2) AS capacity_factor_pct
FROM fact_telemetry_silver t
JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY t.asset_id, date
ORDER BY date DESC, capacity_factor_pct DESC;


-- 2. Fleet Availability % by Site & Country
SELECT 
    a.site,
    a.country,
    ROUND(SUM(CASE WHEN t.status_code IN ('OK', 'CURTAILED') THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id), 2) AS availability_pct
FROM fact_telemetry_silver t
JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY a.site, a.country
ORDER BY availability_pct DESC;


-- 3. Top 5 Worst-Performing Assets (Downtime)
SELECT 
    t.asset_id,
    COUNT(CASE WHEN t.status_code IN ('FAULT', 'OFFLINE') THEN 1 END) AS downtime_records
FROM fact_telemetry_silver t
GROUP BY t.asset_id
ORDER BY downtime_records DESC
LIMIT 5;


-- 4. Fault Code Frequency Breakdown
SELECT 
    t.fault_code,
    COUNT(t.id) AS occurrences
FROM fact_telemetry_silver t
WHERE t.status_code = 'FAULT' AND t.fault_code IS NOT NULL
GROUP BY t.fault_code
ORDER BY occurrences DESC;


-- 5. Daily Generation Comparison: Wind vs. Solar (MWh)
SELECT 
    a.country,
    DATE(t.timestamp) AS date,
    ROUND(SUM(CASE WHEN a.type = 'wind' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS wind_mwh,
    ROUND(SUM(CASE WHEN a.type = 'solar' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS solar_mwh
FROM fact_telemetry_silver t
JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY a.country, date
ORDER BY date DESC, a.country ASC;
