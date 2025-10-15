from __future__ import annotations

from typing import List, Dict, Any
import os
import backoff
from openai import OpenAI


class OpenRouterSummarizer:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def summarize(self, system_prompt: str, user_content: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content
