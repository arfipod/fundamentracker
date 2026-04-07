from __future__ import annotations

import yfinance as yf


def fetch_company_name(ticker: str) -> str:
    info = yf.Ticker(ticker).info
    return info.get("shortName", ticker)


def fetch_current_pe(ticker: str) -> float | None:
    try:
        ticker_info = yf.Ticker(ticker).info
        return ticker_info.get("trailingPE")
    except Exception:
        return None


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
        current_pe = fetch_current_pe(ticker)
        pe_display = f" (Current: {current_pe:.2f})" if current_pe is not None else ""
        message += f"- *{details['name']}* ({ticker}) → PE<{details['pe_trigger']}{pe_display}\n"
    return message


def format_alerts_message(state: dict) -> str:
    if not state["watchlist"]:
        return "🔕 No alerts configured."

    message = "🚨 *Alert Configuration:*\n"
    for ticker, details in state["watchlist"].items():
        current_pe = fetch_current_pe(ticker)
        
        # Determine status based on current PE vs trigger
        is_triggered = current_pe is not None and current_pe < details["pe_trigger"]
        status = "🔔 TRIGGERED" if is_triggered else "⏳ waiting"
        
        # Show current PE if available
        pe_display = f" (Current: {current_pe:.2f})" if current_pe is not None else ""
        
        if is_triggered:
            message += f"- *{details['name']}* ({ticker}) → PE<{details['pe_trigger']}{pe_display} [{status}]\n"
        else:
            message += f"- *{details['name']}* ({ticker}) → PE<{details['pe_trigger']}{pe_display} [{status}]\n"
    return message
