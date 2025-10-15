from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/anthropic/claude-3.5-sonnet")
    notion_api_key: str = ""
    notion_database_id: str = ""

    # Optional third-party keys (leave blank to skip)
    glassnode_api_key: str = ""
    nansen_api_key: str = ""
    laevitas_api_key: str = ""
    coinglass_api_key: str = ""
    hyblock_api_key: str = ""
    arkham_api_key: str = ""

    # HTTP
    timeout_seconds: float = 30.0

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/anthropic/claude-3.5-sonnet"),
            notion_api_key=os.getenv("NOTION_API_KEY", ""),
            notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
            glassnode_api_key=os.getenv("GLASSNODE_API_KEY", ""),
            nansen_api_key=os.getenv("NANSEN_API_KEY", ""),
            laevitas_api_key=os.getenv("LAEVITAS_API_KEY", ""),
            coinglass_api_key=os.getenv("COINGLASS_API_KEY", ""),
            hyblock_api_key=os.getenv("HYBLOCK_API_KEY", ""),
            arkham_api_key=os.getenv("ARKHAM_API_KEY", ""),
        )

    def ensure_minimum(self) -> None:
        missing = []
        if not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if not self.notion_api_key:
            missing.append("NOTION_API_KEY")
        if not self.notion_database_id:
            missing.append("NOTION_DATABASE_ID")
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )
