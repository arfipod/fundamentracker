import os
import sys
import json
import requests
import yfinance as yf
from jsonbin import load_state, save_state

# -------------------------------
# TELEGRAM CONFIG
# -------------------------------

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# -------------------------------
# TELEGRAM HELPERS
# -------------------------------

def send_message(text):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        )
    except:
        print("Failed to send Telegram message")

def get_updates(last_update_id):
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates?offset={last_update_id + 1}")
        return r.json().get("result", [])
    except:
        return []

# -------------------------------
# CLI ARGUMENTS (for GitHub Actions)
# -------------------------------

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--cli", action="store_true")
parser.add_argument("--action")
parser.add_argument("--ticker")
parser.add_argument("--value")
parser.add_argument("--test", action="store_true")
args = parser.parse_args()

# -------------------------------
# TEST MODE
# -------------------------------

if args.test:
    send_message("✅ Test OK: GitHub Actions connected correctly.")
    sys.exit(0)

# -------------------------------
# LOAD STATE FROM JSONBIN
# -------------------------------

state = load_state()

if "watchlist" not in state:
    state = {"watchlist": {}, "last_update_id": 0}

# -------------------------------
# CLI MODE (ADD/REMOVE FROM GITHUB ACTIONS)
# -------------------------------

if args.cli:

    if args.action == "add":
        ticker = args.ticker.upper()
        trigger = float(args.value)

        info = yf.Ticker(ticker).info
        name = info.get("shortName", ticker)

        state["watchlist"][ticker] = {
            "name": name,
            "pe_trigger": trigger,
            "last_pe_alert": None
        }

        save_state(state)
        print(f"✅ Added {ticker} with PE < {trigger}")
        sys.exit(0)

    if args.action == "remove":
        ticker = args.ticker.upper()
        if ticker in state["watchlist"]:
            del state["watchlist"][ticker]
            save_state(state)
            print(f"🗑 Removed {ticker}")
        else:
            print("Ticker not found.")
        sys.exit(0)

# -------------------------------
# TELEGRAM COMMANDS
# -------------------------------

def process_telegram_commands(state):
    updates = get_updates(state["last_update_id"])

    for update in updates:
        state["last_update_id"] = update["update_id"]
        msg = update.get("message", {})
        text = msg.get("text", "")
        parts = text.strip().split()

        # /add TICKER PE
        if parts[0] == "/add" and len(parts) == 3:
            ticker = parts[1].upper()
            trigger = float(parts[2])
            info = yf.Ticker(ticker).info
            name = info.get("shortName", ticker)

            state["watchlist"][ticker] = {
                "name": name,
                "pe_trigger": trigger,
                "last_pe_alert": None
            }
            send_message(f"✅ Added {name} ({ticker}) with P/E < {trigger}")

        elif parts[0] == "/remove" and len(parts) == 2:
            ticker = parts[1].upper()
            if ticker in state["watchlist"]:
                del state["watchlist"][ticker]
                send_message(f"🗑 Removed {ticker}")
            else:
                send_message("❌ Ticker not found.")

        elif parts[0] == "/list":
            if not state["watchlist"]:
                send_message("📭 Watchlist empty.")
            else:
                msg = "📌 *Watchlist:*\n"
                for t, d in state["watchlist"].items():
                    msg += f"- *{d['name']}* ({t}) → PE<{d['pe_trigger']}\n"
                send_message(msg)

        elif parts[0] == "/state":
            send_message(f"📊 *State:*\n```\n{json.dumps(state, indent=2)}\n```")

        elif parts[0] == "/resetstate":
            state["watchlist"] = {}
            state["last_update_id"] = 0
            send_message("♻️ State reset.")

        elif parts[0] == "/help":
            send_message(
                "🛠 Commands:\n"
                "/add TICKER PE\n"
                "/remove TICKER\n"
                "/list\n"
                "/state\n"
                "/resetstate\n"
                "/help"
            )

    return state

state = process_telegram_commands(state)

# -------------------------------
# NO WATCHLIST → EXIT
# -------------------------------

if not state["watchlist"]:
    save_state(state)
    sys.exit(0)

# -------------------------------
# FUNDAMENTAL SCAN
# -------------------------------

for ticker, info in state["watchlist"].items():
    try:
        yf_info = yf.Ticker(ticker).info
        pe = yf_info.get("trailingPE")
        price = yf_info.get("currentPrice")

        if pe is None:
            continue

        trigger = info["pe_trigger"]
        last = info["last_pe_alert"]

        if pe < trigger and (last is None or last >= trigger):
            send_message(
                f"🚨 *FUNDAMENTAL ALERT*\n"
                f"{info['name']} ({ticker}) P/E = {pe:.2f}\n"
                f"Price: ${price}"
            )
            state["watchlist"][ticker]["last_pe_alert"] = pe

        if pe >= trigger and last is not None:
            state["watchlist"][ticker]["last_pe_alert"] = None

    except Exception as e:
        print("Error with", ticker, e)

save_state(state)