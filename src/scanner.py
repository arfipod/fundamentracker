import yfinance as yf


def run_fundamental_scan(state, send_message_func):
    for ticker, details in state["watchlist"].items():
        try:
            ticker_info = yf.Ticker(ticker).info
            pe = ticker_info.get("trailingPE")
            price = ticker_info.get("currentPrice")

            if pe is None:
                continue

            trigger = details["pe_trigger"]
            last_alert_value = details["last_pe_alert"]

            if pe < trigger and (last_alert_value is None or last_alert_value >= trigger):
                send_message_func(
                    "🚨 *FUNDAMENTAL ALERT*\n"
                    f"{details['name']} ({ticker}) P/E = {pe:.2f}\n"
                    f"Price: ${price}"
                )
                state["watchlist"][ticker]["last_pe_alert"] = pe

            if pe >= trigger and last_alert_value is not None:
                state["watchlist"][ticker]["last_pe_alert"] = None

        except Exception as error:
            print("Error with", ticker, error)

    return state
