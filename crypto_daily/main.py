from __future__ import annotations

import argparse
from datetime import datetime, timezone
import pandas as pd

from utils.config import Settings
from providers.binance import fetch_klines
from ta.indicators import ema, rsi, macd, atr, bollinger_bands
from summarizer.openrouter_client import OpenRouterSummarizer
from sinks.notion_writer import NotionWriter


def compute_ta_summary() -> str:
    btc = fetch_klines("BTCUSDT", "1d", 200)
    eth = fetch_klines("ETHUSDT", "1d", 200)

    btc_close = btc["close"]
    eth_close = eth["close"]

    # BTC TA
    btc_ema20 = ema(btc_close, 20).iloc[-1]
    btc_ema50 = ema(btc_close, 50).iloc[-1]
    btc_rsi = rsi(btc_close, 14).iloc[-1]
    btc_macd_line, btc_signal, btc_hist = macd(btc_close)

    # ETH TA
    eth_ema20 = ema(eth_close, 20).iloc[-1]
    eth_ema50 = ema(eth_close, 50).iloc[-1]
    eth_rsi = rsi(eth_close, 14).iloc[-1]
    eth_macd_line, eth_signal, eth_hist = macd(eth_close)
    eth_atr = atr(eth, 14).iloc[-1]
    _, _, _, eth_bbw = bollinger_bands(eth_close)
    eth_bbw_last = eth_bbw.iloc[-1]

    lines = [
        f"BTC: EMA20={btc_ema20:.2f}, EMA50={btc_ema50:.2f}, RSI14={btc_rsi:.1f}, MACD_hist={btc_hist.iloc[-1]:.2f}",
        f"ETH: EMA20={eth_ema20:.2f}, EMA50={eth_ema50:.2f}, RSI14={eth_rsi:.1f}, MACD_hist={eth_hist.iloc[-1]:.2f}, ATR14={eth_atr:.2f}, BBWidth={eth_bbw_last:.4f}",
    ]
    return "\n".join(lines)


def build_user_content(ta_snippet: str) -> str:
    # In production, concatenate content from all providers
    return f"""
Data inputs (summarize and fill placeholders with your analysis):

Technical snapshot
{ta_snippet}

Funding/OI/liquidations: <from Coinglass/Hyblock/Laevitas if available>
On-chain (NUPL/MVRV, flows, whales): <from Glassnode/Nansen/Arkham if available>
Stablecoins & DefiLlama: <stablecoin caps, net flows>
Catalysts (CoinMarketCal): <upcoming events>
Sentiment (social/news): <X/Telegram/Discord>
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ISO date for the page", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.ensure_minimum()

    summarizer = OpenRouterSummarizer(settings.openrouter_api_key, settings.openrouter_model)

    with open("prompts/daily_template.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    ta_snippet = compute_ta_summary()
    user_content = build_user_content(ta_snippet)
    summary = summarizer.summarize(system_prompt, user_content)

    title = f"Crypto Daily - {args.date}"

    if args.dry_run:
        print(title)
        print("\n" + summary)
        return

    notion = NotionWriter(settings.notion_api_key, settings.notion_database_id)
    page_id = notion.create_daily_page(args.date, title, summary)
    print(f"Created Notion page: {page_id}")


if __name__ == "__main__":
    main()
