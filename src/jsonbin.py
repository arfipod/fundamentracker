import os
import requests
import json

JSONBIN_ID = os.getenv("JSONBIN_ID")
JSONBIN_KEY = os.getenv("JSONBIN_KEY")

BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_KEY
}

def load_state():
    try:
        r = requests.get(BASE_URL, headers=HEADERS)
        if r.status_code == 200:
            return r.json()["record"]
        else:
            return {"watchlist": {}, "last_update_id": 0}
    except:
        return {"watchlist": {}, "last_update_id": 0}

def save_state(state):
    try:
        requests.put(BASE_URL, headers=HEADERS, json=state)
    except Exception as e:
        print("Failed to save state:", e)