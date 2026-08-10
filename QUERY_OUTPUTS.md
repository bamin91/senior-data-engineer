# Vattenfall Case Study — SQL Reporting Outputs

This file documents the exact analytical SQL queries and their verified database table outputs generated from the 5-day historical dataset seed (`GET /telemetry/historical?days=5`).

---

## 1. Daily Capacity Factor per Asset
* **Definition:** Total actual energy produced divided by maximum theoretical capacity over the observed period.

```sql
SELECT t.asset_id, DATE(t.timestamp) AS date,
       ROUND(SUM(t.power_output_kw) / (a.rated_capacity_kw * COUNT(t.id)) * 100, 2) AS capacity_factor_pct
FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY t.asset_id, date ORDER BY date DESC, capacity_factor_pct DESC;
```

### Verified Dashboard Run Output

| Index | asset_id | date | capacity_factor_pct |
| :--- | :--- | :--- | :--- |
| 0 | PV-DE-001 | 2026-08-10 | 51.74 |
| 1 | PV-DE-002 | 2026-08-10 | 49.81 |
| 2 | PV-DE-003 | 2026-08-10 | 50.73 |
| 3 | PV-NL-001 | 2026-08-10 | 50.94 |
| 4 | PV-NL-002 | 2026-08-10 | 49.73 |
| 5 | WT-DE-001 | 2026-08-10 | 56.28 |
| 6 | WT-DE-002 | 2026-08-10 | 54.29 |
| 7 | WT-NL-001 | 2026-08-10 | 56.22 |
| 8 | WT-NL-002 | 2026-08-10 | 55.23 |
| 9 | WT-SE-001 | 2026-08-10 | 55.12 |

---

## 2. Fleet Availability % by Site & Country
* **Definition:** Percentage of operational records free of communication loss or mechanical faults.

```sql
SELECT a.site, a.country,
       ROUND(SUM(CASE WHEN t.status_code IN ('OK', 'CURTAILED') THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id), 2) AS availability_pct
FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY a.site, a.country ORDER BY availability_pct DESC;
```
*(Dynamic visualization verified across core operational sites: Boel Wind Farm [SE], DanTysk [DE], Haringvliet Solar Park [NL], Hollandse Kust Zuid [NL], and Neuhardenberg Solar [DE]).*

---

## 3. Top 5 Worst-Performing Assets (Downtime)

```sql
SELECT t.asset_id, COUNT(CASE WHEN t.status_code IN ('FAULT', 'OFFLINE') THEN 1 END) AS downtime_records
FROM fact_telemetry_silver t GROUP BY t.asset_id ORDER BY downtime_records DESC LIMIT 5;
```

### Verified Dashboard Run Output

| Index | asset_id | downtime_records |
| :--- | :--- | :--- |
| 0 | WT-SE-001 | 182 |
| 1 | WT-DE-002 | 179 |
| 2 | PV-NL-002 | 179 |
| 3 | PV-DE-002 | 178 |
| 4 | WT-NL-002 | 174 |

---

## 4. Fault Code Frequency Breakdown

```sql
SELECT t.fault_code, COUNT(t.id) AS occurrences
FROM fact_telemetry_silver t WHERE t.status_code = 'FAULT' AND t.fault_code IS NOT NULL
GROUP BY t.fault_code ORDER BY occurrences DESC;
```

### Verified Dashboard Run Output

| Index | fault_code | occurrences |
| :--- | :--- | :--- |
| 0 | OVERTEMP | 303 |
| 1 | GRID_FAULT | 299 |
| 2 | GEARBOX_VIBRATION | 287 |
| 3 | INVERTER_TRIP | 277 |
| 4 | SENSOR_COMM_LOSS | 256 |

---

## 5. Daily Generation Comparison: Wind vs. Solar (MWh)

```sql
SELECT a.country, DATE(t.timestamp) AS date,
       ROUND(SUM(CASE WHEN a.type = 'wind' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS wind_mwh,
       ROUND(SUM(CASE WHEN a.type = 'solar' THEN t.power_output_kw ELSE 0 END) / 1000.0, 2) AS solar_mwh
FROM fact_telemetry_silver t JOIN dim_assets a ON t.asset_id = a.asset_id
GROUP BY a.country, date ORDER BY date DESC;
```

### Verified Dashboard Run Output

| Index | country | date | wind_mwh | solar_mwh |
| :--- | :--- | :--- | :--- | :--- |
| 0 | DE | 2026-08-10 | 8,932.31 | 2,618.48 |
| 1 | NL | 2026-08-10 | 26,656.02 | 1,132.54 |
| 2 | SE | 2026-08-10 | 13,584.45 | 0.00 |
| 3 | DE | 2026-08-09 | 253.98 | 55.55 |
| 4 | NL | 2026-08-09 | 862.68 | 25.85 |
| 5 | SE | 2026-08-09 | 394.87 | 0.00 |
| 6 | DE | 2026-08-08 | 156.74 | 56.87 |
| 7 | NL | 2026-08-08 | 758.25 | 26.58 |
| 8 | SE | 2026-08-08 | 310.51 | 0.00 |
| 9 | DE | 2026-08-07 | 92.99 | 17.17 |
