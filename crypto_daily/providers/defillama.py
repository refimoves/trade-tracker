from __future__ import annotations

from typing import Any, Dict
import httpx

BASE = "https://api.llama.fi"


def fetch_stablecoin_caps() -> Dict[str, Any]:
    # Example: https://api.llama.fi/stablecoins?includePrices=true
    url = f"{BASE}/stablecoins"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, params={"includePrices": "true"})
        r.raise_for_status()
        return r.json()
