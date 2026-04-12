from __future__ import annotations

import argparse
import os
import sys

import requests

from jsonbin import load_state, save_state
from scanner import run_fundamental_scan
from state import ensure_state_shape
from telegram_service import process_telegram_commands, send_message
from watchlist import add_ticker, format_alerts_message, parse_trigger, remove_ticker

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--action")
    parser.add_argument("--ticker")
    parser.add_argument("--value")
    parser.add_argument("--metric", default="pe")
    parser.add_argument("--operator", default="<")
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def run_test_mode():
    send_message(requests, TELEGRAM_API, CHAT_ID, "✅ Test OK: GitHub Actions connected correctly.")
    sys.exit(0)


def handle_cli_mode(args, state):
    from config import METRICS_MAP, OPERATORS_MAP
    
    if args.action == "add":
        if not args.ticker or args.value is None:
            print("Usage: --cli --action add --ticker TICKER --value TARGET [--metric METRIC] [--operator OP]")
            sys.exit(1)

        try:
            trigger = parse_trigger(args.value)
        except ValueError as error:
            print(error)
            sys.exit(1)

        if args.metric not in METRICS_MAP or args.operator not in OPERATORS_MAP:
            print(f"Invalid metric or operator. Supported metrics: {list(METRICS_MAP.keys())}, Supported operators: {list(OPERATORS_MAP.keys())}")
            sys.exit(1)

        symbol, _ = add_ticker(state, args.ticker, args.metric, args.operator, trigger)
        save_state(state)
        send_message(requests, TELEGRAM_API, CHAT_ID, f"✅ Added {symbol} with {args.metric} {args.operator} {trigger}")
        print(f"✅ Added {symbol} with {args.metric} {args.operator} {trigger}")
        sys.exit(0)

    if args.action == "remove":
        if not args.ticker:
            print("Usage: --cli --action remove --ticker TICKER")
            sys.exit(1)

        removed, symbol = remove_ticker(state, args.ticker)
        if removed:
            save_state(state)
            send_message(requests, TELEGRAM_API, CHAT_ID, f"🗑 Removed {symbol}")
            print(f"🗑 Removed {symbol}")
        else:
            print("Ticker not found.")
        sys.exit(0)

    if args.action == "alerts":
        message = format_alerts_message(state)
        send_message(requests, TELEGRAM_API, CHAT_ID, message)
        print(message)
        sys.exit(0)

    print("Valid actions: add, remove, alerts")
    sys.exit(1)


def main():
    args = parse_args()

    if args.test:
        run_test_mode()

    state = ensure_state_shape(load_state())

    if args.cli:
        handle_cli_mode(args, state)

    state = process_telegram_commands(state, requests, TELEGRAM_API, CHAT_ID)

    if not state["watchlist"]:
        save_state(state)
        sys.exit(0)

    state = run_fundamental_scan(
        state,
        lambda text: send_message(requests, TELEGRAM_API, CHAT_ID, text),
    )

    save_state(state)


if __name__ == "__main__":
    main()
