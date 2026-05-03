import yfinance as yf
import pandas as pd

t = yf.Ticker("AAPL")
q_inc = t.quarterly_incomestmt.T
q_bal = t.quarterly_balancesheet.T

df = pd.concat([q_inc, q_bal], axis=1).sort_index()

for date, row in df.iterrows():
    ni = row.get("Net Income", 0)
    eq = row.get("Stockholders Equity", 0)
    if pd.isna(ni): ni = 0
    if pd.isna(eq): eq = 1
    print(date, ni / eq if eq else 0)

