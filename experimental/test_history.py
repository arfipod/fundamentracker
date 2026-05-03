import yfinance as yf
import pandas as pd

t = yf.Ticker("AAPL")
q_inc = t.quarterly_incomestmt
q_bal = t.quarterly_balancesheet

if not q_inc.empty and not q_bal.empty:
    dates = q_inc.columns
    roes = {}
    for d in dates:
        net_income = q_inc.loc["Net Income", d] if "Net Income" in q_inc.index else 0
        equity = q_bal.loc["Stockholders Equity", d] if "Stockholders Equity" in q_bal.index else 1
        roes[d] = net_income / equity if equity else 0
    
    print(roes)
    
    # how to interpolate?
    roes_series = pd.Series(roes).sort_index()
    print(roes_series)
