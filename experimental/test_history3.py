import yfinance as yf
import pandas as pd
import numpy as np

t = yf.Ticker("AAPL")
hist = t.history(period="1y")

try:
    q_inc = t.quarterly_incomestmt.T if t.quarterly_incomestmt is not None else pd.DataFrame()
    q_bal = t.quarterly_balancesheet.T if t.quarterly_balancesheet is not None else pd.DataFrame()
    q_df = pd.concat([q_inc, q_bal], axis=1, sort=True).sort_index()
except Exception as e:
    print(f"Error: {e}")
    q_df = pd.DataFrame()

# We want ROE = Net Income / Stockholders Equity
# Let's create a Series for ROE
if not q_df.empty:
    roes = []
    dates = []
    for date, row in q_df.iterrows():
        ni = row.get("Net Income", 0)
        eq = row.get("Stockholders Equity", 0)
        if pd.isna(ni) or pd.isna(eq) or eq == 0:
            continue
        roes.append(ni / eq * 100)
        dates.append(date)
    
    roe_series = pd.Series(roes, index=dates).sort_index()
    
    # reindex roe_series to hist.index, using forward fill
    # hist.index is timezone-aware usually, roe_series index might be naive
    roe_series.index = pd.to_datetime(roe_series.index)
    if hist.index.tz is not None and roe_series.index.tz is None:
        roe_series.index = roe_series.index.tz_localize(hist.index.tz)

    # combine and forward fill
    combined = pd.concat([hist["Close"], roe_series], axis=1, keys=["Close", "ROE"])
    combined["ROE"] = combined["ROE"].ffill()
    
    # fill any remaining NaNs with the first available ROE
    combined["ROE"] = combined["ROE"].bfill()

    for date, row in combined.iterrows():
        if pd.notna(row["Close"]):
            print(f"{date.strftime('%Y-%m-%d')}: {row['ROE']}")
            break
