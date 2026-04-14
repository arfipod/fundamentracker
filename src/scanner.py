import yfinance as yf

from config import METRICS_MAP, OPERATORS_MAP


from watchlist import get_yf_session

def run_fundamental_scan(state, send_message_func):
    for ticker, details in list(state["watchlist"].items()):
        try:
            ticker_info = yf.Ticker(ticker, session=get_yf_session()).info
            price = ticker_info.get("currentPrice", "N/A")
            
            for alert in details.get("alerts", []):
                metric = alert["metric"]
                op_str = alert["operator"]
                target = alert["target"]
                
                if metric not in METRICS_MAP or op_str not in OPERATORS_MAP:
                    continue
                    
                val = ticker_info.get(METRICS_MAP[metric])
                if val is None:
                    continue
                    
                op_func = OPERATORS_MAP[op_str]
                is_triggered = op_func(val, target)
                was_triggered = alert.get("is_triggered", False)
                
                if is_triggered and not was_triggered:
                    send_message_func(
                        "🚨 *FUNDAMENTAL ALERT*\n"
                        f"{details['name']} ({ticker}) {metric} = {val:.2f}\n"
                        f"Condition: {metric} {op_str} {target}\n"
                        f"Price: ${price}"
                    )
                    alert["is_triggered"] = True
                elif not is_triggered and was_triggered:
                    alert["is_triggered"] = False

        except Exception as error:
            print("Error with", ticker, error)

    return state

