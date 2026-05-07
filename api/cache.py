from market_data.providers.yfinance_provider import YFinanceProvider

_provider = YFinanceProvider()

def get_ticker_info(ticker: str) -> dict:
    try:
        return _provider.get_quote(ticker)
    except Exception:
        return {}

def get_tickers_info_batch(tickers: list[str]) -> dict:
    results = {}
    for ticker in tickers:
        symbol = ticker.upper()
        try:
            results[symbol] = _provider.get_quote(symbol)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            results[symbol] = {}
            
    return results
