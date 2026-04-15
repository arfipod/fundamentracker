import time
import yfinance as yf

YF_CACHE = {}
CACHE_TTL = 120

def get_ticker_info(ticker: str) -> dict:
    now = time.time()
    ticker = ticker.upper()
    
    if ticker in YF_CACHE:
        cached_time, data = YF_CACHE[ticker]
        if now - cached_time < CACHE_TTL:
            return data

    try:
        data = yf.Ticker(ticker).info
        YF_CACHE[ticker] = (now, data)
        return data
    except Exception:
        return {}

def get_tickers_info_batch(tickers: list[str]) -> dict:
    now = time.time()
    results = {}
    to_fetch = []
    
    for t in tickers:
        t = t.upper()
        if t in YF_CACHE:
            cached_time, data = YF_CACHE[t]
            if now - cached_time < CACHE_TTL:
                results[t] = data
                continue
        to_fetch.append(t)
        
    if to_fetch:
        try:
            yf_tickers = yf.Tickers(" ".join(to_fetch))
            for t in to_fetch:
                # yf.Tickers returns an object with a .tickers dictionary
                try:
                    data = yf_tickers.tickers[t].info
                    YF_CACHE[t] = (now, data)
                    results[t] = data
                except Exception as inner_e:
                    print(f"Error fetching {t}: {inner_e}")
                    results[t] = {}
        except Exception as e:
            print(f"Batch fetch error: {e}")
            
    return results
