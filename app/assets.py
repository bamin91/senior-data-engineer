"""
Static asset registry for the telemetry source service.

Represents a small fleet of Vattenfall-style renewable generation assets
(wind turbines and solar inverters) spread across a few sites/countries.
This is intentionally static/in-memory -- candidates are not expected to
build asset management, just to consume this as reference/dimension data.
"""

ASSETS = [
    # Wind turbines - Sweden, Boel Wind Farm
    {"asset_id": "WT-SE-001", "type": "wind", "country": "SE", "site": "Boel Wind Farm", "rated_capacity_kw": 3600, "commissioned": "2019-04-01"},
    {"asset_id": "WT-SE-002", "type": "wind", "country": "SE", "site": "Boel Wind Farm", "rated_capacity_kw": 3600, "commissioned": "2019-04-01"},
    {"asset_id": "WT-SE-003", "type": "wind", "country": "SE", "site": "Boel Wind Farm", "rated_capacity_kw": 3600, "commissioned": "2019-04-15"},
    # Wind turbines - Netherlands, Hollandse Kust
    {"asset_id": "WT-NL-001", "type": "wind", "country": "NL", "site": "Hollandse Kust Zuid", "rated_capacity_kw": 11000, "commissioned": "2023-01-10"},
    {"asset_id": "WT-NL-002", "type": "wind", "country": "NL", "site": "Hollandse Kust Zuid", "rated_capacity_kw": 11000, "commissioned": "2023-01-10"},
    # Wind turbines - Germany, DanTysk
    {"asset_id": "WT-DE-001", "type": "wind", "country": "DE", "site": "DanTysk", "rated_capacity_kw": 3600, "commissioned": "2015-03-20"},
    {"asset_id": "WT-DE-002", "type": "wind", "country": "DE", "site": "DanTysk", "rated_capacity_kw": 3600, "commissioned": "2015-03-20"},
    # Solar inverters - Netherlands, Haringvliet
    {"asset_id": "PV-NL-001", "type": "solar", "country": "NL", "site": "Haringvliet Solar Park", "rated_capacity_kw": 500, "commissioned": "2021-06-01"},
    {"asset_id": "PV-NL-002", "type": "solar", "country": "NL", "site": "Haringvliet Solar Park", "rated_capacity_kw": 500, "commissioned": "2021-06-01"},
    # Solar inverters - Germany
    {"asset_id": "PV-DE-001", "type": "solar", "country": "DE", "site": "Neuhardenberg Solar", "rated_capacity_kw": 750, "commissioned": "2020-09-12"},
    {"asset_id": "PV-DE-002", "type": "solar", "country": "DE", "site": "Neuhardenberg Solar", "rated_capacity_kw": 750, "commissioned": "2020-09-12"},
    {"asset_id": "PV-DE-003", "type": "solar", "country": "DE", "site": "Neuhardenberg Solar", "rated_capacity_kw": 750, "commissioned": "2020-09-12"},
]


def get_assets():
    return ASSETS


def get_asset(asset_id: str):
    for a in ASSETS:
        if a["asset_id"] == asset_id:
            return a
    return None
