"""
Synthetic telemetry generator.

Simulates a batch of SCADA/IoT readings arriving from the field for a
mix of wind and solar assets. Each call to generate_batch() represents
"whatever showed up since you last polled" -- batch size and asset mix
are randomized, and a configurable fraction of readings are deliberately
malformed to simulate real-world sensor/network issues:

  - null / missing required fields
  - out-of-range values (negative output, impossible wind speed, etc.)
  - duplicate readings (same asset_id + timestamp sent twice)
  - out-of-order timestamps (a "late" reading older than others in the batch)
  - orphan readings (asset_id not in the registry)

Candidates are expected to detect and handle these in their ingestion
pipeline, not to make this generator disappear.
"""

import random
from datetime import datetime, timedelta, timezone

from app.assets import get_assets

BAD_DATA_RATE = 0.15  # ~15% of readings have a data quality issue


def _clean_reading(asset: dict, ts: datetime) -> dict:
    reading = {
        "asset_id": asset["asset_id"],
        "timestamp": ts.isoformat(),
        "status_code": random.choices(
            ["OK", "CURTAILED", "FAULT", "OFFLINE"],
            weights=[85, 8, 5, 2],
        )[0],
        "fault_code": None,
    }

    if asset["type"] == "wind":
        wind_speed = round(random.uniform(0, 22), 2)
        # simple, not-physically-precise power curve
        capacity_factor = min(1.0, max(0.0, (wind_speed - 3) / 12)) if wind_speed >= 3 else 0.0
        reading.update({
            "wind_speed_ms": wind_speed,
            "blade_pitch_deg": round(random.uniform(0, 30), 1),
            "rotor_rpm": round(random.uniform(5, 18), 1),
            "power_output_kw": round(asset["rated_capacity_kw"] * capacity_factor, 1),
        })
    else:  # solar
        hour = ts.hour + ts.minute / 60
        # crude daylight bell curve, zero output at night
        daylight = max(0.0, 1 - ((hour - 13) / 7) ** 2) if 6 <= hour <= 20 else 0.0
        irradiance = round(daylight * random.uniform(700, 1000), 1)
        reading.update({
            "irradiance_wm2": irradiance,
            "panel_temp_c": round(15 + daylight * random.uniform(10, 25), 1),
            "power_output_kw": round(asset["rated_capacity_kw"] * daylight * random.uniform(0.85, 1.0), 1),
        })

    if reading["status_code"] == "FAULT":
        reading["fault_code"] = random.choice(
            ["SENSOR_COMM_LOSS", "OVERTEMP", "GRID_FAULT", "INVERTER_TRIP", "GEARBOX_VIBRATION"]
        )
        reading["power_output_kw"] = 0.0
    elif reading["status_code"] == "OFFLINE":
        reading["power_output_kw"] = 0.0

    return reading


def _corrupt_reading(reading: dict) -> dict:
    """Apply exactly one randomly-chosen data quality issue to a reading."""
    issue = random.choice([
        "null_field",
        "out_of_range",
        "orphan_asset",
        "missing_asset_id",
        "stale_timestamp",
    ])

    if issue == "null_field":
        field = random.choice(["power_output_kw", "wind_speed_ms", "irradiance_wm2", "status_code"])
        if field in reading:
            reading[field] = None

    elif issue == "out_of_range":
        if "power_output_kw" in reading:
            reading["power_output_kw"] = round(random.uniform(-500, -1), 1)
        elif "wind_speed_ms" in reading:
            reading["wind_speed_ms"] = round(random.uniform(60, 150), 1)  # physically implausible

    elif issue == "orphan_asset":
        reading["asset_id"] = f"WT-XX-{random.randint(900, 999)}"  # not in registry

    elif issue == "missing_asset_id":
        reading["asset_id"] = None

    elif issue == "stale_timestamp":
        # simulate a reading that arrives very late (e.g. buffered by a flaky
        # field gateway) -- timestamp is much older than the rest of the batch
        old_ts = datetime.now(timezone.utc) - timedelta(hours=random.randint(6, 48))
        reading["timestamp"] = old_ts.isoformat()

    return reading


def generate_historical(days: int = 5, interval_minutes: int = 60) -> list[dict]:
    """
    One-shot bulk backfill covering the previous `days` days, at a fixed
    reading interval per asset. Meant to be pulled once (e.g. at pipeline
    startup) so reporting queries that group by day have more than a
    single partial day to work with -- /telemetry/next-batch alone only
    ever reflects the last couple of minutes of wall-clock time.

    Carries the same data-quality issues as generate_batch(), since real
    historical telemetry would have gone through the same messy field
    conditions.
    """
    assets = get_assets()
    now = datetime.now(timezone.utc)
    total_steps = int(days * 24 * 60 / interval_minutes)

    readings = []
    for asset in assets:
        for step in range(total_steps, 0, -1):
            ts = now - timedelta(minutes=step * interval_minutes)
            reading = _clean_reading(asset, ts)
            if random.random() < BAD_DATA_RATE:
                reading = _corrupt_reading(reading)
            readings.append(reading)

    # sprinkle in outright duplicates, same as the live stream
    duplicate_count = int(len(readings) * 0.02)
    for _ in range(duplicate_count):
        readings.append(dict(random.choice(readings)))

    random.shuffle(readings)
    return readings


def generate_batch(min_size: int = 5, max_size: int = 25) -> list[dict]:
    assets = get_assets()
    batch_size = random.randint(min_size, max_size)
    now = datetime.now(timezone.utc)

    readings = []
    for _ in range(batch_size):
        asset = random.choice(assets)
        # jitter timestamps slightly so they're not all identical
        ts = now - timedelta(seconds=random.randint(0, 90))
        reading = _clean_reading(asset, ts)

        if random.random() < BAD_DATA_RATE:
            reading = _corrupt_reading(reading)

        readings.append(reading)

    # occasionally duplicate a reading outright (same asset_id + timestamp
    # sent twice, e.g. a gateway retry) -- independent of BAD_DATA_RATE
    if readings and random.random() < 0.2:
        readings.append(dict(random.choice(readings)))

    random.shuffle(readings)
    return readings
