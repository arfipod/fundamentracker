import os
import sys
import json
import requests
import yfinance as yf

# -------------------------------
# CONFIG
# -------------------------------

STATE_FILE = "data/state.json"
os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# -------------------------------
# STATE HANDLING
# -------------------------------

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"watchlist": {}, "last_update_id": 0}

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        # Corrupted or unreadable state → reset
        return {"watchlist": {}, "last_update_id": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


state = load_state()

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
    # ✅ FIXED bug: last_header_id → last_update_id
    url = f"{TELEGRAM_API}/getUpdates?offset={last_update_id + 1}"
    try:
        r = requests.get(url)
        return r.json().get("result", [])
    except:
        return []


# -------------------------------
# COMMAND PARSER
# -------------------------------

def process_telegram_commands(state):
    updates = get_updates(state["last_update_id"])
    if not updates:
        return state

    for update in updates:
        state["last_update_id"] = update["update_id"]
        msg = update.get("message", {})
        text = msg.get("text", "")
        parts = text.strip().split()

        # ---------------- COMMAND: /add ----------------
        if parts[0].lower() == "/add" and len(parts) == 3:
            ticker = parts[1].upper()
            try:
                trigger = float(parts[2])
            except:
                send_message("❌ Wrong format. Use: `/add TICKER PE`")
                continue

            try:
                info = yf.Ticker(ticker).info
                name = info.get("shortName", ticker)
            except:
                name = ticker

            state["watchlist"][ticker] = {
                "name": name,
                "pe_trigger": trigger,
                "last_pe_alert": None
            }

            send_message(f"✅ Added *{name}* ({ticker}) with P/E trigger < {trigger}")

        # ---------------- COMMAND: /remove ----------------
        elif parts[0].lower() == "/remove" and len(parts) == 2:
            ticker = parts[1].upper()
            if ticker in state["watchlist"]:
                del state["watchlist"][ticker]
                send_message(f"🗑 Removed {ticker}")
            else:
                send_message("❌ Ticker not found in watchlist.")

        # ---------------- COMMAND: /list ----------------
        elif parts[0].lower() == "/list":
            if not state["watchlist"]:
                send_message("📭 *Watchlist is empty*")
            else:
                msg = "📌 *Current watchlist:*\n\n"
                for t, d in state["watchlist"].items():
                    msg += f"- *{d['name']}* ({t}) → P/E<{d['pe_trigger']}\n"
                send_message(msg)

        # ---------------- COMMAND: /state ----------------
        elif parts[0].lower() == "/state":
            pretty = json.dumps(state, indent=2)
            send_message(f"📊 *Current State:*\n```\n{pretty}\n```")

        # ---------------- COMMAND: /resetstate ----------------
        elif parts[0].lower() == "/resetstate":
            state["watchlist"] = {}
            state["last_update_id"] = 0
            send_message("♻️ *State reset.* Watchlist cleared and counters set to zero.")

        # ---------------- HELP ----------------
        elif parts[0].lower() == "/help":
            send_message(
                "🛠 *Available Commands:*\n"
                "/add TICKER PE → Add a new company\n"
                "/remove TICKER → Remove a company\n"
                "/list → Show all companies\n"
                "/state → Show internal state\n"
                "/resetstate → Reset internal state\n"
                "/help → Show this message"
            )

    return state


# -------------------------------
# TEST MODE
# -------------------------------

if len(sys.argv) > 1 and sys.argv[1] == "--test":
    send_message("✅ *Test OK:* GitHub Actions is connected correctly.")
    sys.exit(0)


# -------------------------------
# PROCESS TELEGRAM COMMANDS
# -------------------------------

state = process_telegram_commands(state)

# Nothing to monitor?
if not state["watchlist"]:
    save_state(state)
    sys.exit(0)

# -------------------------------
# 15-MINUTE FUNDAMENTAL SCAN
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

        # NEW alert?
        if pe < trigger and (last_alert is None or last_alert >= trigger):
            send_message(
                f"🚨 *FUNDAMENTAL ALERT*\n\n"
                f"*{info['name']}* ({ticker}) dropped to P/E *{pe:.2f}*\n"
                f"Current Price: ${price}"
            )
            state["watchlist"][ticker]["last_pe_alert"] = pe

        # Reset alert flag if P/E returns above threshold
        if pe >= trigger and last_alert is not None:
            state["watchlist"][ticker]["last_pe_alert"] = None

    except Exception as e:
        print(f"❌ Error with {ticker}: {e}")

# -------------------------------
# SAVE STATE
# -------------------------------
save_state(state)