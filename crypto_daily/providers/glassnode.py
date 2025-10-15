from __future__ import annotations

from typing import Any, Dict, Optional
import httpx

BASE = "https://api.glassnode.com/v1"


def fetch_metric(api_key: str, metric: str, a: str = "BTC", i: str = "24h") -> Any:
    # e.g., metric="metrics/indicators/mvrv_z_score"
    url = f"{BASE}/{metric}"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, params={"a": a, "i": i, "api_key": api_key})
        r.raise_for_status()
        return r.json()
