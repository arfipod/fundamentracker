import os
import requests

from state import default_state

JSONBIN_ID = os.getenv("JSONBIN_ID")
JSONBIN_KEY = os.getenv("JSONBIN_KEY")

BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_KEY,
}


def load_state():
    try:
        response = requests.get(BASE_URL, headers=HEADERS)
        if response.status_code == 200:
            return response.json()["record"]
        return default_state()
    except Exception:
        return default_state()


def save_state(state):
    try:
        requests.put(BASE_URL, headers=HEADERS, json=state)
    except Exception as error:
        print("Failed to save state:", error)
