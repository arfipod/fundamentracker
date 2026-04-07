import os
import sys
from typing import Callable, Dict, Iterable, List

import requests
import yfinance as yf

# Securely load credentials from Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Your watchlist (You can expand this as needed)
WATCHLIST = [
    {"ticker": "AAPL", "name": "Apple"},
    {"ticker": "TSLA", "name": "Tesla"},
    {"ticker": "NVO", "name": "Novo Nordisk"},
]


def send_telegram_alert(
    message: str,
    token: str = TOKEN,
    chat_id: str = CHAT_ID,
    post: Callable = requests.post,
) -> bool:
    """Send a Telegram alert message and return whether it succeeded."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"Failed to send Telegram message: {exc}")
        return False


def build_valuation_alert(company_name: str, ticker: str, pe: float, price: float) -> str:
    """Build a markdown valuation alert payload."""
    return (
        "🚨 *VALUATION ALERT* 🚨\n\n"
        f"The company *{company_name}* ({ticker}) now has a P/E of *{pe:.2f}*.\n"
        f"Current Price: ${price}"
    )


def run_scan(
    watchlist: Iterable[Dict[str, str]] = WATCHLIST,
    ticker_factory: Callable = yf.Ticker,
    alert_sender: Callable[[str], bool] = send_telegram_alert,
) -> List[str]:
    """Run the fundamental scan and return tickers that triggered an alert."""
    print("Starting 15-minute fundamental scan...")
    alerted_tickers: List[str] = []

    for item in watchlist:
        ticker = item["ticker"]
        try:
            data = ticker_factory(ticker).info
            price = data.get("currentPrice")
            pe = data.get("trailingPE")

            # Example Alert Condition: If P/E falls below 25
            if pe and pe < 25:
                msg = build_valuation_alert(item["name"], ticker, pe, price)
                alert_sender(msg)
                alerted_tickers.append(ticker)
                print(f"Alert sent for {ticker}")

        except Exception as exc:
            print(f"Error processing {ticker}: {exc}")

    print("Scan completed.")
    return alerted_tickers


def run_connection_test(alert_sender: Callable[[str], bool] = send_telegram_alert) -> None:
    """Send a test message and exit flow for connectivity checks."""
    print("Running connection test...")
    test_msg = "🚀 *FundamenTracker Test*: Your GitHub Action is connected successfully!"
    alert_sender(test_msg)
    print("Test message sent. Exiting.")


def main(argv: List[str] | None = None) -> int:
    """CLI entrypoint."""
    args = argv if argv is not None else sys.argv[1:]

    if args and args[0] == "--test":
        run_connection_test()
        return 0

    run_scan()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
