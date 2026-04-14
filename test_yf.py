import yfinance as yf
try:
    print(yf.Ticker('AAPL').info['shortName'])
except Exception as e:
    print("Error:", e)
