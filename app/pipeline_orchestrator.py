import sys
import os
import time
import sqlite3
import requests
import logging
import json
from datetime import datetime, timezone

# Ensure absolute logging metrics and system tracing entries
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VattenfallPOCPipeline")

SOURCE_URL = "http://localhost:8000"
DB_PATH = "vattenfall_lakehouse.db"
POLLING_INTERVAL_SECONDS = 10

def init_database():
    """Initializes the physical analytical Star Schema model matching Gold Layer guidelines."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Dimension Table: Fleet Static Asset Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_assets (
            asset_id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            country TEXT NOT NULL,
            site TEXT NOT NULL,
            rated_capacity_kw REAL NOT NULL,
            commissioned TEXT NOT NULL
        )
    """)
    
    # 2. Fact Table: Clean Unified Silver Telemetry (Atomic Data Base Layer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_telemetry_silver (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT,
            timestamp TEXT NOT NULL,
            status_code TEXT NOT NULL,
            fault_code TEXT,
            power_output_kw REAL NOT NULL,
            wind_speed_ms REAL,
            blade_pitch_deg REAL,
            rotor_rpm REAL,
            irradiance_wm2 REAL,
            panel_temp_c REAL,
            is_imputed INTEGER DEFAULT 0,
            ingested_at TEXT NOT NULL
        )
    """)
    
    # 3. Isolation Quarantine Layer (Audit Trail and Compliance Safeguard)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarantine_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_payload TEXT NOT NULL,
            rejection_reason TEXT NOT NULL,
            quarantined_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database schemas and Star Schema layout successfully initialized.")

def populate_dim_assets():
    """Syncs Fleet Static Asset Registry from source service endpoints into dim_assets."""
    try:
        response = requests.get(f"{SOURCE_URL}/assets", timeout=5)
        response.raise_for_status()
        assets = response.json()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for asset in assets:
            cursor.execute("""
                INSERT OR REPLACE INTO dim_assets (asset_id, type, country, site, rated_capacity_kw, commissioned)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (asset['asset_id'], asset['type'], asset['country'], asset['site'], asset['rated_capacity_kw'], asset['commissioned']))
        conn.commit()
        conn.close()
        logger.info("Static Asset registry successfully synchronized to dim_assets layer.")
    except Exception as e:
        logger.error(f"Failed to fetch dimension data registry assets: {str(e)}")

def get_valid_asset_ids():
    """Fetches valid asset registry boundary check markers from dim_assets."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT asset_id FROM dim_assets")
    asset_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return asset_ids

def parse_and_validate_reading(reading: dict, valid_asset_ids: set) -> tuple[bool, str, dict]:
    """Defensively validates and sanitizes a single payload entry record."""
    asset_id = reading.get("asset_id")
    ts_str = reading.get("timestamp")
    status_code = reading.get("status_code")
    
    # 1. Detect Orphan or Missing Asset IDs
    if not asset_id:
        return False, "REJECTED_MISSING_ASSET_ID", reading
    if asset_id not in valid_asset_ids:
        return False, "QUARANTINED_ORPHAN_ASSET_ID", reading
        
    # 2. Detect missing structural timestamps
    if not ts_str:
        return False, "REJECTED_MISSING_TIMESTAMP", reading

    # 3. Handle Timestamps
    try:
        datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return False, "REJECTED_MALFORMED_TIMESTAMP", reading

    # 4. Impute Null Status Codes Defensively
    is_imputed = 0
    if not status_code:
        status_code = "OK"
        is_imputed = 1

    power_output = reading.get("power_output_kw")
    # 5. Out of Range validation corrections and quarantines
    if power_output is not None:
        if float(power_output) < 0:
            return False, "QUARANTINED_NEGATIVE_POWER_OUTPUT", reading
    else:
        if status_code in ["FAULT", "OFFLINE"]:
            power_output = 0.0
            is_imputed = 1
        else:
            return False, "QUARANTINED_NULL_POWER_OUTPUT", reading

    wind_speed = reading.get("wind_speed_ms")
    if wind_speed is not None and float(wind_speed) > 60.0:
        return False, "QUARANTINED_IMPLAUSIBLE_WIND_SPEED", reading

    clean_record = {
        "asset_id": asset_id,
        "timestamp": ts_str,
        "status_code": status_code,
        "fault_code": reading.get("fault_code"),
        "power_output_kw": float(power_output),
        "wind_speed_ms": float(wind_speed) if wind_speed is not None else None,
        "blade_pitch_deg": float(reading.get("blade_pitch_deg")) if reading.get("blade_pitch_deg") is not None else None,
        "rotor_rpm": float(reading.get("rotor_rpm")) if reading.get("rotor_rpm") is not None else None,
        "irradiance_wm2": float(reading.get("irradiance_wm2")) if reading.get("irradiance_wm2") is not None else None,
        "panel_temp_c": float(reading.get("panel_temp_c")) if reading.get("panel_temp_c") is not None else None,
        "is_imputed": is_imputed,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    
    return True, "CLEAN", clean_record

def ingest_batch_payloads(batch: list):
    """Ingests, deduplicates and materializes telemetry array data rows natively."""
    if not batch:
        return
    
    valid_assets = get_valid_asset_ids()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    clean_records = []
    quarantine_records = []
    seen_dedup_keys = set()
    
    for reading in batch:
        is_valid, reason, parsed_data = parse_and_validate_reading(reading, valid_assets)
        
        if is_valid:
            # Inline sliding-window deduplication check
            dedup_key = (parsed_data["asset_id"], parsed_data["timestamp"])
            if dedup_key in seen_dedup_keys:
                continue
            seen_dedup_keys.add(dedup_key)
            
            # Double check schema collision history in database
            cursor.execute(
                "SELECT 1 FROM fact_telemetry_silver WHERE asset_id = ? AND timestamp = ?", 
                (parsed_data["asset_id"], parsed_data["timestamp"])
            )
            if cursor.fetchone():
                continue
                
            clean_records.append((
                parsed_data["asset_id"], parsed_data["timestamp"], parsed_data["status_code"],
                parsed_data["fault_code"], parsed_data["power_output_kw"], parsed_data["wind_speed_ms"],
                parsed_data["blade_pitch_deg"], parsed_data["rotor_rpm"], parsed_data["irradiance_wm2"],
                parsed_data["panel_temp_c"], parsed_data["is_imputed"], parsed_data["ingested_at"]
            ))
        else:
            quarantine_records.append((
                json.dumps(reading), reason, datetime.now(timezone.utc).isoformat()
            ))
            
    if clean_records:
        cursor.executemany("""
            INSERT INTO fact_telemetry_silver (
                asset_id, timestamp, status_code, fault_code, power_output_kw,
                wind_speed_ms, blade_pitch_deg, rotor_rpm, irradiance_wm2, panel_temp_c, is_imputed, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, clean_records)
        
    if quarantine_records:
        cursor.executemany("""
            INSERT INTO quarantine_telemetry (raw_payload, rejection_reason, quarantined_at)
            VALUES (?, ?, ?)
        """, quarantine_records)
        
    conn.commit()
    logger.info(f"Pipeline Batch Committed: {len(clean_records)} Clean Rows | {len(quarantine_records)} Quarantined Elements.")
    conn.close()

def run_historical_seeding():
    """Triggers high-volume historic database configuration backfill at startup."""
    logger.info("Initializing Historical Backfill Seeding Run (5 Days requested)...")
    try:
        response = requests.get(f"{SOURCE_URL}/telemetry/historical?days=5", timeout=15)
        response.raise_for_status()
        historical_batch = response.json().get("batch", [])
        ingest_batch_payloads(historical_batch)
        logger.info("Historical seeding lifecycle fully completed and established.")
    except Exception as e:
        logger.error(f"Critical error during historical backfill execution stage: {str(e)}")

def run_continuous_polling_loop():
    """Launches event-driven live polling extraction cycle loop against next-batch microservices."""
    logger.info("Starting live stream tracking ingestion process loop...")
    while True:
        try:
            response = requests.get(f"{SOURCE_URL}/telemetry/next-batch?min_size=10&max_size=25", timeout=5)
            response.raise_for_status()
            batch = response.json().get("batch", [])
            ingest_batch_payloads(batch)
        except Exception as e:
            logger.error(f"Polling loop exception experienced: {str(e)}")
        time.sleep(POLLING_INTERVAL_SECONDS)

if __name__ == '__main__':
    init_database()
    populate_dim_assets()
    run_historical_seeding()
    run_continuous_polling_loop()
