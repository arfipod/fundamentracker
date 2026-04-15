from __future__ import annotations

import yfinance as yf

from config import METRICS_MAP, OPERATORS_MAP
try:
    from watchlist import format_alerts_message, format_watchlist_message
except Exception as e:
    print(e)
    
from db import client as db

HELP_TEXT = """🛠 Commands:
/add TICKER VALUE (defaults to pe < VALUE)
/add TICKER METRIC OP VALUE
/remove TICKER
/list
/alerts
/help"""

LAST_UPDATE_ID = 0

def send_message(requests_client, api_base: str, chat_id: str, text: str) -> None:
    try:
        requests_client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_updates(requests_client, api_base: str, last_update_id: int) -> list[dict]:
    try:
        response = requests_client.get(f"{api_base}/getUpdates?offset={last_update_id + 1}", timeout=10)
        res_json = response.json()
        if not response.ok:
            pass
        return res_json.get("result", [])
    except Exception as e:
        return []

def process_telegram_commands(requests_client, api_base: str) -> None:
    global LAST_UPDATE_ID
    updates = get_updates(requests_client, api_base, LAST_UPDATE_ID)
    
    for update in updates:
        LAST_UPDATE_ID = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "")
        sender_chat_id = message.get("chat", {}).get("id")
        if not sender_chat_id:
             continue
             
        print(f"Processing command: {text}", flush=True)
        parts = text.strip().split()

        if not parts:
            continue

        if parts[0] == "/add" and len(parts) >= 3:
            try:
                trigger = float(parts[-1])
                ticker = parts[1].upper()
                
                if len(parts) == 3:
                    metric = "pe"
                    op = "<"
                elif len(parts) == 5:
                    metric = parts[2].lower()
                    op = parts[3]
                else:
                    send_message(requests_client, api_base, sender_chat_id, "❌ Usage: /add TICKER METRIC OP VALUE (or /add TICKER PE_VALUE)")
                    continue

                if metric not in METRICS_MAP or op not in OPERATORS_MAP:
                    send_message(requests_client, api_base, sender_chat_id, f"❌ Invalid metric or operator.")
                    continue
                
                name = ticker
                try:
                    t_info = yf.Ticker(ticker).info
                    name = t_info.get("shortName", ticker)
                except:
                    pass
                    
                db.add_ticker_db(ticker, name)
                db.add_alert_db(ticker, metric, op, trigger)
                
                send_message(
                    requests_client,
                    api_base,
                    sender_chat_id,
                    f"✅ Added {name} ({ticker}) with {metric} {op} {trigger}",
                )
            except ValueError:
                send_message(requests_client, api_base, sender_chat_id, "❌ Invalid value. Use a valid number.")

        elif parts[0] == "/remove" and len(parts) == 2:
            res = db.delete_ticker_db(parts[1].upper())
            if res:
                send_message(requests_client, api_base, sender_chat_id, f"🗑 Removed {parts[1].upper()}")
            else:
                send_message(requests_client, api_base, sender_chat_id, "❌ Ticker not found.")

        elif parts[0] == "/list":
            send_message(requests_client, api_base, sender_chat_id, format_watchlist_message(db))

        elif parts[0] == "/alerts":
            send_message(requests_client, api_base, sender_chat_id, format_alerts_message(db))

        elif parts[0] == "/help":
            send_message(requests_client, api_base, sender_chat_id, HELP_TEXT)

        else:
            send_message(requests_client, api_base, sender_chat_id, "❓ Unknown command.\n" + HELP_TEXT)
