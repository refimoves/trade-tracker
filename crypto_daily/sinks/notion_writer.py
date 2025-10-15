from __future__ import annotations

from typing import Dict, Any
from notion_client import Client
from datetime import datetime, timezone


class NotionWriter:
    def __init__(self, api_key: str, database_id: str):
        self.client = Client(auth=api_key)
        self.database_id = database_id

    def create_daily_page(self, date_key: str, title: str, content_markdown: str) -> str:
        # Assumes database has properties: Name (title), Date (date), Tags (multi_select)
        page = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties={
                "Name": {"title": [{"text": {"content": title}}]},
                "Date": {"date": {"start": date_key}},
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content_markdown}}]
                    },
                }
            ],
        )
        return page.get("id")
