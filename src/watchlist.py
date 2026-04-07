from __future__ import annotations

import yfinance as yf


def fetch_company_name(ticker: str) -> str:
    info = yf.Ticker(ticker).info
    return info.get("shortName", ticker)


def parse_trigger(value: str) -> float:
    trigger = float(value)
    if trigger <= 0:
        raise ValueError("Trigger value must be greater than zero.")
    return trigger


def add_ticker(state: dict, ticker: str, trigger: float) -> tuple[str, str]:
    symbol = ticker.upper()
    name = fetch_company_name(symbol)

    state["watchlist"][symbol] = {
        "name": name,
        "pe_trigger": trigger,
        "last_pe_alert": None,
    }

    return symbol, name


def remove_ticker(state: dict, ticker: str) -> tuple[bool, str]:
    symbol = ticker.upper()

    if symbol in state["watchlist"]:
        del state["watchlist"][symbol]
        return True, symbol

    return False, symbol


def format_watchlist_message(state: dict) -> str:
    if not state["watchlist"]:
        return "📭 Watchlist empty."

    message = "📌 *Watchlist:*\n"
    for ticker, details in state["watchlist"].items():
        message += f"- *{details['name']}* ({ticker}) → PE<{details['pe_trigger']}\n"
    return message
