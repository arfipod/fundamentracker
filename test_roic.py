import yfinance as yf

t = yf.Ticker("AAPL")
info = t.info

print("returnOnCapitalEmployed in info:", "returnOnCapitalEmployed" in info)

inc = t.incomestmt
bal = t.balancesheet

print("Inc cols:", inc.columns)
print("Inc idx:", inc.index[:5])
print("Bal cols:", bal.columns)
print("Bal idx:", bal.index[:5])

if not inc.empty and not bal.empty:
    date = inc.columns[0]
    ebit = inc.loc["EBIT", date] if "EBIT" in inc.index else 0
    tax_provision = inc.loc["Tax Provision", date] if "Tax Provision" in inc.index else 0
    pretax_income = inc.loc["Pretax Income", date] if "Pretax Income" in inc.index else 0
    
    tax_rate = tax_provision / pretax_income if pretax_income else 0.21
    nopat = ebit * (1 - tax_rate)
    
    total_debt = bal.loc["Total Debt", date] if "Total Debt" in bal.index else 0
    equity = bal.loc["Stockholders Equity", date] if "Stockholders Equity" in bal.index else 0
    
    roic = nopat / (total_debt + equity) if (total_debt + equity) != 0 else 0
    print("Computed ROIC:", roic)
