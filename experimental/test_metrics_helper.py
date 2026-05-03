import yfinance as yf
import pandas as pd

t = yf.Ticker("AAPL")

def get_historical_fundamental(t, metric_name, hist_index):
    q_inc = t.quarterly_incomestmt.T if t.quarterly_incomestmt is not None else pd.DataFrame()
    q_bal = t.quarterly_balancesheet.T if t.quarterly_balancesheet is not None else pd.DataFrame()
    
    try:
        q_df = pd.concat([q_inc, q_bal], axis=1, sort=True).sort_index()
    except:
        q_df = pd.DataFrame()
        
    if q_df.empty:
        return pd.Series(index=hist_index, dtype=float)

    values = []
    dates = []
    
    for date, row in q_df.iterrows():
        val = None
        if metric_name == "roe":
            ni = row.get("Net Income", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.notna(ni) and pd.notna(eq) and eq != 0:
                val = (ni / eq) * 100
                
        elif metric_name == "roic":
            ebit = row.get("EBIT", 0)
            if pd.isna(ebit):
                # Approximation: Pretax Income + Interest Expense
                pi = row.get("Pretax Income", 0)
                ie = row.get("Interest Expense", 0)
                ebit = (pi if pd.notna(pi) else 0) + (ie if pd.notna(ie) else 0)
                
            tp = row.get("Tax Provision", 0)
            pi = row.get("Pretax Income", 0)
            tax_rate = tp / pi if pd.notna(tp) and pd.notna(pi) and pi != 0 else 0.21
            nopat = ebit * (1 - tax_rate)
            
            debt = row.get("Total Debt", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.isna(debt): debt = 0
            if pd.isna(eq): eq = 0
            
            if (debt + eq) != 0:
                val = (nopat / (debt + eq)) * 100
                
        elif metric_name == "debttoequity":
            debt = row.get("Total Debt", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.notna(debt) and pd.notna(eq) and eq != 0:
                val = debt / eq
                
        elif metric_name == "profitmargins":
            ni = row.get("Net Income", 0)
            tr = row.get("Total Revenue", 0)
            if pd.notna(ni) and pd.notna(tr) and tr != 0:
                val = (ni / tr) * 100
                
        elif metric_name == "operatingmargins":
            oi = row.get("Operating Income", 0)
            tr = row.get("Total Revenue", 0)
            if pd.notna(oi) and pd.notna(tr) and tr != 0:
                val = (oi / tr) * 100

        if val is not None:
            values.append(val)
            dates.append(date)
            
    series = pd.Series(values, index=dates).sort_index()
    series.index = pd.to_datetime(series.index)
    if hist_index.tz is not None and series.index.tz is None:
        series.index = series.index.tz_localize(hist_index.tz)
        
    combined = pd.concat([pd.Series(index=hist_index, dtype=float), series], axis=1)
    combined = combined.iloc[:, 1].ffill().bfill()
    return combined.loc[hist_index]

hist = t.history(period="1y")
print("ROE head:")
print(get_historical_fundamental(t, "roe", hist.index).head())
print("ROIC head:")
print(get_historical_fundamental(t, "roic", hist.index).head())
print("DebtToEquity head:")
print(get_historical_fundamental(t, "debttoequity", hist.index).head())
