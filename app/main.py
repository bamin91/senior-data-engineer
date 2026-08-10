"""
Telemetry source service -- simulates the field/SCADA side of a renewable
generation fleet (wind + solar). This is the "Source App" candidates build
their ingestion pipeline against; it is NOT part of the pipeline itself.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException

from app.assets import get_assets, get_asset
from app.generator import generate_batch, generate_historical

app = FastAPI(
    title="Vattenfall Renewable Telemetry Source (simulated)",
    description=(
        "Simulated SCADA/IoT telemetry source for a small wind + solar fleet. "
        "Poll /telemetry/next-batch to receive new readings, the way a real "
        "ingestion job would poll a field gateway or subscribe to a queue."
    ),
    version="1.0.0",
)

_historical_cache: dict[int, list] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/assets")
def list_assets():
    """Static asset registry (dimension data) for the fleet."""
    return get_assets()


@app.get("/assets/{asset_id}")
def get_asset_by_id(asset_id: str):
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset


@app.get("/telemetry/next-batch")
def next_batch(min_size: int = 5, max_size: int = 25):
    """
    Returns a batch of telemetry readings that have "arrived" since the
    last call. Call this repeatedly (e.g. on a schedule/poll loop) to
    simulate an ongoing telemetry stream.

    Batches are NOT guaranteed clean: expect nulls, out-of-range values,
    duplicates, orphan asset_ids, and occasional out-of-order timestamps.
    That's intentional -- your ingestion pipeline should handle it.
    """
    if min_size < 1 or max_size < min_size:
        raise HTTPException(status_code=400, detail="invalid min_size/max_size")
    return {
        "batch": generate_batch(min_size=min_size, max_size=max_size),
    }


@app.get("/telemetry/historical")
def historical_backfill(days: int = 5):
    """
    One-shot bulk backfill of the previous `days` days of readings (default
    5), so you don't need to run a live poller for days just to have
    enough data for day-over-day / multi-day reporting queries. Call this
    once at pipeline startup to seed your store, then use
    /telemetry/next-batch for the ongoing "live" stream.

    Same data-quality caveats apply as next-batch: expect nulls,
    out-of-range values, duplicates, and orphan asset_ids. Results are
    cached per `days` value, so repeated calls return the same dataset.
    """
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="days must be between 1 and 30")
    if days not in _historical_cache:
        _historical_cache[days] = generate_historical(days=days)
    return {"batch": _historical_cache[days]}
