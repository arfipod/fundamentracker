from __future__ import annotations

import logging

from config import METRICS_MAP, OPERATORS_MAP
from market_data.service import get_market_data_service

try:
    from watchlist import format_alerts_message, format_watchlist_message
except Exception:
    logging.getLogger(__name__).exception("Failed to import Telegram watchlist formatters")

from repositories.factory import get_repository

logger = logging.getLogger(__name__)
db = get_repository()

HELP_TEXT = """🛠 Commands:
/add TICKER VALUE (defaults to pe < VALUE)
/add TICKER METRIC OP VALUE
/remove TICKER
/list
/alerts
/help"""

LAST_UPDATE_ID = 0


def _safe_telegram_error(error: Exception, api_base: str) -> str:
    message = str(error)
    if api_base:
        message = message.replace(api_base, "https://api.telegram.org/bot<redacted>")
    return message[:500]


def send_message(requests_client, api_base: str, chat_id: str, text: str) -> None:
    try:
        requests_client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as error:
        logger.warning(
            "Failed to send Telegram message",
            extra={
                "error_type": type(error).__name__,
                "error": _safe_telegram_error(error, api_base),
            },
        )

def get_updates(requests_client, api_base: str, last_update_id: int) -> list[dict]:
    try:
        response = requests_client.get(f"{api_base}/getUpdates?offset={last_update_id + 1}", timeout=10)
        res_json = response.json()
        if not response.ok:
            pass
        return res_json.get("result", [])
    except Exception as error:
        logger.warning(
            "Failed to fetch Telegram updates",
            extra={
                "error_type": type(error).__name__,
                "error": _safe_telegram_error(error, api_base),
            },
        )
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
             
        parts = text.strip().split()

        if not parts:
            continue
        command = parts[0]
        ticker = parts[1].upper() if len(parts) > 1 else None
        logger.info(
            "Processing Telegram command",
            extra={"telegram_command": command, "ticker": ticker},
        )

        if command == "/add" and len(parts) >= 3:
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
                    quote = get_market_data_service().get_quote(ticker)
                    name = quote.get("shortName", quote.get("name", ticker))
                except Exception as error:
                    logger.warning(
                        "Failed to fetch company name for Telegram add command",
                        extra={
                            "ticker": ticker,
                            "metric": "quote",
                            "provider": getattr(get_market_data_service().provider, "source", None),
                        },
                        exc_info=error,
                    )
                    
                db.add_ticker_db(ticker, name)
                db.add_alert_db(ticker, metric, op, trigger)
                logger.info(
                    "Telegram command added alert",
                    extra={"ticker": ticker, "metric": metric},
                )
                
                send_message(
                    requests_client,
                    api_base,
                    sender_chat_id,
                    f"✅ Added {name} ({ticker}) with {metric} {op} {trigger}",
                )
            except ValueError:
                send_message(requests_client, api_base, sender_chat_id, "❌ Invalid value. Use a valid number.")

        elif command == "/remove" and len(parts) == 2:
            res = db.delete_ticker_db(parts[1].upper())
            logger.info("Telegram command removed ticker", extra={"ticker": parts[1].upper()})
            if res:
                send_message(requests_client, api_base, sender_chat_id, f"🗑 Removed {parts[1].upper()}")
            else:
                send_message(requests_client, api_base, sender_chat_id, "❌ Ticker not found.")

        elif command == "/list":
            send_message(requests_client, api_base, sender_chat_id, format_watchlist_message(db))

        elif command == "/alerts":
            send_message(requests_client, api_base, sender_chat_id, format_alerts_message(db))

        elif command == "/help":
            send_message(requests_client, api_base, sender_chat_id, HELP_TEXT)

        else:
            send_message(requests_client, api_base, sender_chat_id, "❓ Unknown command.\n" + HELP_TEXT)
