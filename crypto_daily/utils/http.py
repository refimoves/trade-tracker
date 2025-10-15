from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from .config import Settings


def create_client(settings: Settings) -> httpx.Client:
    headers = {
        "User-Agent": "crypto-daily/0.1",
    }
    return httpx.Client(timeout=settings.timeout_seconds, headers=headers)


def get_json(client: httpx.Client, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
    resp = client.get(url, params=params or {}, headers=headers)
    resp.raise_for_status()
    return resp.json()
