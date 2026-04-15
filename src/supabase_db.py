import os
import requests
from state import default_state

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BASE_URL = f"{SUPABASE_URL}/rest/v1/app_state"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def load_state():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials are missing. Using default state.")
        return default_state()

    try:
        response = requests.get(f"{BASE_URL}?id=eq.1&select=state", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]["state"]
        return default_state()
    except Exception as error:
        print("Error loading state from Supabase:", error)
        return default_state()

def save_state(state):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    try:
        headers = HEADERS.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        payload = {"id": 1, "state": state}

        response = requests.post(BASE_URL, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as error:
        print("Error saving state to Supabase:", error)
