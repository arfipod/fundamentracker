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

        # ---------------- COMMAND: ADD ----------------
        if parts[0].lower() == "/add" and len(parts) == 3:
            ticker = parts[1].upper()
            try:
                trigger = float(parts[2])
            except:
                send_message("❌ Formato incorrecto. Uso: `/add TICKER PE`")
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

            send_message(f"✅ Añadido *{name}* ({ticker}) con trigger PE < {trigger}")

        # ---------------- COMMAND: REMOVE ----------------
        elif parts[0].lower() == "/remove" and len(parts) == 2:
            ticker = parts[1].upper()
            if ticker in state["watchlist"]:
                del state["watchlist"][ticker]
                send_message(f"🗑 Eliminado {ticker}")
            else:
                send_message("❌ Ese ticker no estaba en la lista.")

        # ---------------- COMMAND: LIST ----------------
        elif parts[0].lower() == "/list":
            if not state["watchlist"]:
                send_message("📭 *Watchlist vacía*")
            else:
                msg = "📌 *Watchlist actual:*\n\n"
                for t, d in state["watchlist"].items():
                    msg += f"- *{d['name']}* ({t}) → PE<{d['pe_trigger']}\n"
                send_message(msg)

        # ---------------- HELP ----------------
        elif parts[0].lower() == "/help":
            send_message(
                "🛠 *Comandos disponibles:*\n"
                "/add TICKER PE → Añade empresa\n"
                "/remove TICKER → Elimina empresa\n"
                "/list → Lista empresas\n"
                "/help → Ayuda"
            )

    return state


# -------------------------------
# TEST MODE
# -------------------------------

if len(sys.argv) > 1 and sys.argv[1] == "--test":
    send_message("✅ *Test OK:* GitHub Actions conectado correctamente.")
    sys.exit(0)


# -------------------------------
# PROCESS TELEGRAM COMMANDS
# -------------------------------

state = process_telegram_commands(state)

# If watchlist empty → nothing to do
if not state["watchlist"]:
    save_state(state)
    sys.exit(0)

# -------------------------------
# 15 MIN SCAN
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
                f"🚨 *ALERTA FUNDAMENTAL*\n\n"
                f"*{info['name']}* ({ticker}) ha bajado a P/E *{pe:.2f}*\n"
                f"Precio actual: ${price}"
            )
            state["watchlist"][ticker]["last_pe_alert"] = pe

        # Reset if normalized
        if pe >= trigger and last_alert is not None:
            state["watchlist"][ticker]["last_pe_alert"] = None

    except Exception as e:
        print(f"❌ Error con {ticker}: {e}")

# -------------------------------
# SAVE STATE
# -------------------------------
save_state(state)