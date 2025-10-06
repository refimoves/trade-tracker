import os
import time
import hmac
import hashlib
import requests
import pandas as pd

# ================== CONFIG (from GitHub Secrets) ==================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
LIMIT = 50
CLEAR_DB_BEFORE_UPDATE = True
# ================================================================

BASE_URL = "https://api.bybit.com"


# ---- Helper: Sign Bybit request ----
def sign_request(string_to_sign):
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


# ---- Detect all symbols with trades ----
def get_traded_symbols(limit=LIMIT):
    print("Fetching Bybit trades...")
    print("API Key:", BYBIT_API_KEY[:8] + "********")
    possible_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    traded_symbols = set()
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    for sym in possible_symbols:
        params = {
            "category": "spot",
            "symbol": sym,
            "limit": str(limit)
        }
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        string_to_sign = timestamp + BYBIT_API_KEY + recv_window + query
        signature = sign_request(string_to_sign)
        headers = {
            "X-BAPI-API-KEY": BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature
        }
        url = f"{BASE_URL}/v5/execution/list"

        # --- Debug section ---
        response = requests.get(url, headers=headers, params=params)
        print(f"🔍 Checking {sym}: status={response.status_code}")
        try:
            print("Response:", response.text[:400])  # limit output size
        except Exception as e:
            print("Error printing response:", e)
        # ---------------------

        if response.status_code != 200:
            continue
        data = response.json()
        trades_list = data.get("result", {}).get("list", [])
        if trades_list:
            traded_symbols.add(sym)

    return list(traded_symbols)


# ---- Fetch trades from Bybit ----
def get_bybit_trades(symbol, limit=LIMIT):
    endpoint = f"{BASE_URL}/v5/execution/list"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    params = {
        "category": "spot",
        "symbol": symbol,
        "limit": str(limit)
    }
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    string_to_sign = timestamp + BYBIT_API_KEY + recv_window + query
    signature = sign_request(string_to_sign)
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "X-BAPI-SIGN": signature
    }

    url = f"{endpoint}?{query}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Bybit API error {response.status_code}: {response.text}")
        return []

    data = response.json()
    trades_list = data.get("result", {}).get("list", [])

    trades = []
    for t in trades_list:
        qty = float(t.get("execQty", t.get("orderQty", 0)))
        price = float(t.get("execPrice", t.get("avgPrice", 0)))

        exec_time_raw = int(t.get("execTime", 0))
        exec_time = pd.to_datetime(exec_time_raw, unit="ms", errors="coerce")

        fee_crypto = float(t.get("execFee", 0))
        fee_usd = fee_crypto * price if fee_crypto > 0 else 0

        trades.append({
            "Symbol": t.get("symbol", ""),
            "Side": t.get("side", ""),
            "Qty": qty,
            "Entry Price": price,
            "Exec Time": exec_time,
            "Fee $": fee_usd
        })

    return trades


# ---- Map Bybit symbol to Coinbase ----
def bybit_to_coinbase(symbol):
    return symbol.replace("USDT", "")


# ---- Get price (Coinbase first, fallback Bybit) ----
def get_prices(symbols):
    prices = {}
    for s in symbols:
        coin = bybit_to_coinbase(s)
        url_cb = f"https://api.coinbase.com/v2/prices/{coin}-USD/spot"
        try:
            response = requests.get(url_cb, timeout=5)
            if response.status_code == 200:
                data = response.json()
                prices[s] = float(data["data"]["amount"])
                continue
        except Exception:
            pass

        url_bb = f"{BASE_URL}/spot/v3/public/quote/ticker/price?symbol={s}"
        try:
            response = requests.get(url_bb, timeout=5)
            if response.status_code == 200:
                data = response.json()
                prices[s] = float(data["result"]["price"])
                continue
        except Exception:
            pass

        prices[s] = 0.0
        print(f"⚠️ Could not fetch price for {s}")
    return prices


# ---- Build PnL table ----
def build_trade_pnl():
    symbols = get_traded_symbols()
    print("Detected symbols with trades:", symbols)
    all_trades = []
    if not symbols:
        return pd.DataFrame()

    prices = get_prices(symbols)

    for s in symbols:
        trades = get_bybit_trades(s)
        current_price = prices.get(s, 0)
        for t in trades:
            entry_value = t["Qty"] * t["Entry Price"]
            current_value = t["Qty"] * current_price
            pnl = (current_value - entry_value) if t["Side"] == "Buy" else (entry_value - current_value)
            pnl_after_fee = pnl - t["Fee $"]
            pnl_pct = (pnl / entry_value * 100) if entry_value != 0 else 0
            pnl_pct_after_fee = (pnl_after_fee / entry_value * 100) if entry_value != 0 else 0

            emoji = "🟢" if pnl_pct_after_fee >= 0 else "🔴"

            t["Entry Value $"] = entry_value
            t["Current Price $"] = current_price
            t["Current Value $"] = current_value
            t["PnL $"] = pnl
            t["PnL %"] = pnl_pct
            t["PnL after Fee $"] = pnl_after_fee
            t["PnL after Fee %"] = f"{emoji} {round(pnl_pct_after_fee, 2)}%"

            all_trades.append(t)

    df = pd.DataFrame(all_trades)
    expected_cols = [
        "Symbol", "Side", "Qty", "Entry Price", "Entry Value $",
        "Current Price $", "Current Value $", "Fee $",
        "PnL $", "PnL %", "PnL after Fee $", "PnL after Fee %", "Exec Time"
    ]
    return df.reindex(columns=expected_cols)


# ---- Clear Notion database ----
def clear_notion_database():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json={})
    data = response.json()
    pages = data.get("results", [])
    for p in pages:
        page_id = p["id"]
        requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            json={"archived": True}
        )


# ---- Push DataFrame to Notion ----
def push_to_notion(df):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    for _, row in df.iterrows():
        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Symbol": {"title": [{"text": {"content": str(row["Symbol"])}}]},
                "Side": {"rich_text": [{"text": {"content": str(row["Side"])}}]},
                "Qty": {"number": row["Qty"]},
                "Entry Price": {"number": row["Entry Price"]},
                "Entry Value $": {"number": row["Entry Value $"]},
                "Current Price $": {"number": row["Current Price $"]},
                "Current Value $": {"number": row["Current Value $"]},
                "Fee $": {"number": row["Fee $"]},
                "PnL $": {"number": row["PnL $"]},
                "PnL %": {"number": row["PnL %"]},
                "PnL after Fee $": {"number": row["PnL after Fee $"]},
                "PnL after Fee %": {"rich_text": [{"text": {"content": str(row["PnL after Fee %"])}}]},
                "Exec Time": {
                    "date": {
                        "start": row["Exec Time"].isoformat() if pd.notnull(row["Exec Time"]) else None
                    }
                },
            },
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code not in [200, 201]:
            print(f"Failed to push row: {row['Symbol']} - {response.text}")


# ---- MAIN ----
if __name__ == "__main__":
    df = build_trade_pnl()
    print(df)

    if df.empty:
        print("⚠️ No trades found or API returned empty results.")
    else:
        if CLEAR_DB_BEFORE_UPDATE:
            clear_notion_database()
        push_to_notion(df)
        print("✅ Sync complete.")
