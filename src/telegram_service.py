from __future__ import annotations

import json

from watchlist import add_ticker, format_alerts_message, format_watchlist_message, parse_trigger, remove_ticker

HELP_TEXT = (
    "🛠 Commands:\n"
    "/add TICKER PE\n"
    "/remove TICKER\n"
    "/list\n"
    "/alerts\n"
    "/state\n"
    "/resetstate\n"
    "/help"
)


def send_message(requests_client, api_base: str, chat_id: str, text: str) -> None:
    try:
        requests_client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )
    except Exception:
        print("Failed to send Telegram message")


def get_updates(requests_client, api_base: str, last_update_id: int) -> list[dict]:
    try:
        response = requests_client.get(f"{api_base}/getUpdates?offset={last_update_id + 1}")
        return response.json().get("result", [])
    except Exception:
        return []


def process_telegram_commands(state: dict, requests_client, api_base: str, chat_id: str) -> dict:
    updates = get_updates(requests_client, api_base, state["last_update_id"])

    for update in updates:
        state["last_update_id"] = update["update_id"]
        text = update.get("message", {}).get("text", "")
        parts = text.strip().split()

        if not parts:
            continue

        if parts[0] == "/add" and len(parts) == 3:
            try:
                trigger = parse_trigger(parts[2])
                symbol, name = add_ticker(state, parts[1], trigger)
                send_message(
                    requests_client,
                    api_base,
                    chat_id,
                    f"✅ Added {name} ({symbol}) with P/E < {trigger}",
                )
            except ValueError:
                send_message(requests_client, api_base, chat_id, "❌ Invalid PE value. Use a positive number.")

        elif parts[0] == "/remove" and len(parts) == 2:
            removed, symbol = remove_ticker(state, parts[1])
            if removed:
                send_message(requests_client, api_base, chat_id, f"🗑 Removed {symbol}")
            else:
                send_message(requests_client, api_base, chat_id, "❌ Ticker not found.")

        elif parts[0] == "/list":
            send_message(requests_client, api_base, chat_id, format_watchlist_message(state))

        elif parts[0] == "/alerts":
            send_message(requests_client, api_base, chat_id, format_alerts_message(state))

        elif parts[0] == "/state":
            send_message(
                requests_client,
                api_base,
                chat_id,
                f"📊 *State:*\n```\n{json.dumps(state, indent=2)}\n```",
            )

        elif parts[0] == "/resetstate":
            state["watchlist"] = {}
            state["last_update_id"] = 0
            send_message(requests_client, api_base, chat_id, "♻️ State reset.")

        elif parts[0] == "/help":
            send_message(requests_client, api_base, chat_id, HELP_TEXT)

        else:
            send_message(requests_client, api_base, chat_id, "❓ Unknown command.\n" + HELP_TEXT)

    return state
