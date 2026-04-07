import os
import sys
import json
import requests
import yfinance as yf
from jsonbin import load_state, save_state

# -------------------------------
# CONFIG
# -------------------------------

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# -------------------------------
# TELEGRAM HELPERS
# -------------------------------

def send_message(text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_updates(last_update_id):
    url = f"{TELEGRAM_API}/getUpdates?offset={last_update_id + 1}"
    try:
        r = requests.get(url)
        return r.json().get("result", [])
    except:
        return []

# -------------------------------
# PROCESS TELEGRAM COMMANDS
# -------------------------------

def process_telegram_commands(state):
    updates = get_updates(state.get("last_update_id", 0))
    if not updates:
        return state

    for update in updates:
        state["last_update_id"] = update["update_id"]
        msg = update.get("message", {})
        text = msg.get("text", "")
        parts = text.strip().split()

        # /add TICKER PE
        if parts[0].lower() == "/add" and len(parts) == 3:
            ticker = parts[1].upper()
            try:
                trigger = float(parts[2])
            except:
                send_message("❌ Wrong format. Use: `/add TICKER PE`")
                continue

            info = yf.Ticker(ticker).info
            name = info.get("shortName", ticker)

            state["watchlist"][ticker] = {
                "name": name,
                "pe_trigger": trigger,
                "last_pe_alert": None
            }

            send_message(f"✅ Added *{name}* ({ticker}) with P/E < {trigger}")

        elif parts[0].lower() == "/remove" and len(parts) == 2:
            ticker = parts[1].upper()
            if ticker in state["watchlist"]:
                del state["watchlist"][ticker]
                send_message(f"🗑 Removed {ticker}")
            else:
                send_message("❌ Ticker not in watchlist.")

        elif parts[0].lower() == "/list":
            if not state["watchlist"]:
                send_message("📭 Watchlist is empty")
            else:
                msg = "📌 *Current Watchlist:*\n\n"
                for t, d in state["watchlist"].items():
                    msg += f"- *{d['name']}* ({t}) → PE<{d['pe_trigger']}\n"
                send_message(msg)

        elif parts[0].lower() == "/state":
            pretty = json.dumps(state, indent=2)
            send_message(f"📊 *Current State:*\n```\n{pretty}\n```")

        elif parts[0].lower() == "/resetstate":
            state["watchlist"] = {}
            state["last_update_id"] = 0
            send_message("♻️ State reset.")

        elif parts[0].lower() == "/help":
            send_message(
                "🛠 *Commands:*\n"
                "/add TICKER PE\n"
                "/remove TICKER\n"
                "/list\n"
                "/state\n"
                "/resetstate\n"
                "/help"
            )

    return state

# -------------------------------
# TEST MODE
# -------------------------------

if len(sys.argv) > 1 and sys.argv[1] == "--test":
    send_message("✅ Test OK: GitHub Actions is working.")
    sys.exit(0)

# --------------------------------
# LOAD STATE
# --------------------------------

state = load_state()
if "watchlist" not in state:
    state = {"watchlist": {}, "last_update_id": 0}

state = process_telegram_commands(state)

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
        last_alert = info["last_pe_alert"]

        if pe < trigger and (last_alert is None or last_alert >= trigger):
            send_message(
                f"🚨 *FUNDAMENTAL ALERT*\n\n"
                f"*{info['name']}* ({ticker}) dropped to P/E *{pe:.2f}*\n"
                f"Price: ${price}"
            )
            state["watchlist"][ticker]["last_pe_alert"] = pe

        if pe >= trigger and last_alert is not None:
            state["watchlist"][ticker]["last_pe_alert"] = None

    except Exception as e:
        print(f"Error processing {ticker}: {e}")

save_state(state)