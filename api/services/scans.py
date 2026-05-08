from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Callable

import requests

from scanner import run_fundamental_scan
from telegram_service import process_telegram_commands, send_message


def perform_scan(db_client: Any) -> None:
    print("\n--- Executing Fundamental Scan ---", flush=True)
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    telegram_api = f"https://api.telegram.org/bot{token}" if token else ""

    def send_telegram_alert(text: str) -> None:
        if not token or not chat_id:
            return
        send_message(requests, telegram_api, chat_id, text)

    run_fundamental_scan(send_telegram_alert)
    db_client.update_scan_settings_db(last_scan_time=int(time.time()))


async def run_telegram_polling() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return

    telegram_api = f"https://api.telegram.org/bot{token}"

    while True:
        try:
            process_telegram_commands(requests, telegram_api)
        except Exception as error:
            print(f"Telegram polling error: {error}")

        await asyncio.sleep(5)


async def run_periodic_scan(db_client: Any, run_scan: Callable[[], None]) -> None:
    while True:
        try:
            settings = db_client.get_scan_settings_db()
            interval = settings.get("interval_seconds", 0)
            if interval > 0:
                last_time = settings.get("last_scan_time", 0)
                now = int(time.time())
                if now - last_time >= interval:
                    run_scan()
        except Exception as error:
            print(f"Error in background scan: {error}")

        await asyncio.sleep(5)
