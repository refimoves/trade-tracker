from __future__ import annotations

from typing import Any, Dict, List
import httpx
import os

BASE = "https://developers.coinmarketcal.com/v1"


def fetch_events(api_key: str, maxEvents: int = 10) -> List[Dict[str, Any]]:
    # CoinMarketCal requires API key header
    headers = {"x-api-key": api_key}
    url = f"{BASE}/events"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers=headers, params={"max": maxEvents})
        r.raise_for_status()
        data = r.json()
        return data.get("body", [])
