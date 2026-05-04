import yfinance as yf
import pandas as pd
import warnings

# Suppress warnings for cleaner console output during exploration
warnings.filterwarnings('ignore')

def run_capabilities_radar(ticker_symbol="AAPL"):
    """
    Performs a full sweep of the yfinance library capabilities for a given ticker.
    This acts as a 'radar' to show developers exactly what data structures,
    metrics, and dataframes are available to extract.
    """
    print("=" * 80)
    print(f"📡 INITIALIZING YFINANCE CAPABILITIES RADAR FOR: [{ticker_symbol}]")
    print("=" * 80)
    
    # Initialize the Ticker object
    stock = yf.Ticker(ticker_symbol)
    
    # ---------------------------------------------------------
    # 1. THE INFO DICTIONARY (Metadata, Fundamental Ratios, Profile)
    # ---------------------------------------------------------
    print("\n[1] THE 'INFO' DICTIONARY (Core Fundamentals & Metadata)")
    print("-" * 60)
    try:
        info = stock.info
        print(f"➤ Total Key-Value pairs available: {len(info)}")
        
        # Categorize a few important keys to demonstrate what's inside
        categories = {
            "Company Profile": ['shortName', 'sector', 'industry', 'fullTimeEmployees', 'country'],
            "Valuation & Price": ['marketCap', 'trailingPE', 'forwardPE', 'priceToBook', 'pegRatio', 'currentPrice'],
            "Dividends & Yield": ['dividendYield', 'dividendRate', 'payoutRatio', 'exDividendDate'],
            "Financial Health": ['debtToEquity', 'returnOnEquity', 'operatingMargins', 'freeCashflow']
        }
        
        for category, keys in categories.items():
            print(f"  • {category} Samples:")
            for k in keys:
                # Truncate long strings for cleaner console output
                val = str(info.get(k, 'N/A'))[:50] 
                print(f"      - {k}: {val}")
    except Exception as e:
        print(f"❌ Error fetching info: {e}")

    # ---------------------------------------------------------
    # 2. HISTORICAL MARKET DATA (Price Action, Volume)
    # ---------------------------------------------------------
    print("\n[2] HISTORICAL MARKET DATA (.history)")
    print("-" * 60)
    try:
        # Fetching 1 month of daily data
        hist = stock.history(period="1mo", interval="1d")
        if not hist.empty:
            print(f"➤ Data Shape (1mo, 1d interval): {hist.shape} (Rows, Columns)")
            print(f"➤ Columns available: {list(hist.columns)}")
            print(f"➤ Latest Close Price: ${hist['Close'].iloc[-1]:.2f}")
        else:
            print("➤ Historical data returned empty.")
    except Exception as e:
        print(f"❌ Error fetching history: {e}")

    # ---------------------------------------------------------
    # 3. FINANCIAL STATEMENTS (The Accounting Data)
    # ---------------------------------------------------------
    print("\n[3] FINANCIAL STATEMENTS (Annual & Quarterly)")
    print("-" * 60)
    
    statements = {
        "Annual Income Statement": stock.financials,
        "Quarterly Income Statement": stock.quarterly_financials,
        "Annual Balance Sheet": stock.balance_sheet,
        "Quarterly Balance Sheet": stock.quarterly_balance_sheet,
        "Annual Cash Flow": stock.cashflow,
        "Quarterly Cash Flow": stock.quarterly_cashflow
    }
    
    for name, df in statements.items():
        if df is not None and not df.empty:
            print(f"➤ {name}: Available! Shape: {df.shape} (Metrics, Years/Quarters)")
            # Print the top 3 metric names available in the index
            print(f"    Sample Metrics: {list(df.index[:3])}...")
        else:
             print(f"➤ {name}: Not Available / Empty.")

    # ---------------------------------------------------------
    # 4. HOLDERS & OWNERSHIP STRUCTURE
    # ---------------------------------------------------------
    print("\n[4] OWNERSHIP & HOLDERS")
    print("-" * 60)
    
    holders_data = {
        "Major Holders": stock.major_holders,
        "Institutional Holders": stock.institutional_holders,
        "Mutual Fund Holders": stock.mutualfund_holders
    }
    
    for name, df in holders_data.items():
        if df is not None and not df.empty:
            print(f"➤ {name}: Available! Shape: {df.shape}")
        else:
            print(f"➤ {name}: Not Available.")

    # ---------------------------------------------------------
    # 5. CORPORATE ACTIONS (Dividends & Splits)
    # ---------------------------------------------------------
    print("\n[5] CORPORATE ACTIONS")
    print("-" * 60)
    print(f"➤ Dividends Recorded: {len(stock.dividends)} records")
    if len(stock.dividends) > 0:
        print(f"    Latest Dividend: {stock.dividends.iloc[-1]} (Date: {stock.dividends.index[-1].date()})")
        
    print(f"➤ Splits Recorded: {len(stock.splits)} records")
    if len(stock.splits) > 0:
        print(f"    Latest Split: {stock.splits.iloc[-1]} (Date: {stock.splits.index[-1].date()})")

    # ---------------------------------------------------------
    # 6. OPTIONS MARKET
    # ---------------------------------------------------------
    print("\n[6] OPTIONS CHAIN (Derivatives)")
    print("-" * 60)
    try:
        expirations = stock.options
        print(f"➤ Available Expiration Dates: {len(expirations)}")
        if expirations:
            nearest_expiry = expirations[0]
            opt = stock.option_chain(nearest_expiry)
            print(f"    Nearest Expiry ({nearest_expiry}): {len(opt.calls)} Call Options | {len(opt.puts)} Put Options")
    except Exception as e:
        print("➤ Options data not available or failed to load.")

    # ---------------------------------------------------------
    # 7. ANALYST COVERAGE & FORWARD EVENTS
    # ---------------------------------------------------------
    print("\n[7] ANALYST ESTIMATES & EARNINGS DATES")
    print("-" * 60)
    
    try:
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            print(f"➤ Recommendations Shape: {recs.shape}")
        else:
            print("➤ Recommendations: N/A")
            
        upgrades = stock.upgrades_downgrades
        if upgrades is not None and not upgrades.empty:
            print(f"➤ Upgrades/Downgrades Shape: {upgrades.shape}")
        else:
            print("➤ Upgrades/Downgrades: N/A")
            
        earnings = stock.earnings_dates
        if earnings is not None and not earnings.empty:
             print(f"➤ Earnings Dates Calendar Shape: {earnings.shape}")
        else:
             print("➤ Earnings Dates Calendar: N/A")
    except Exception:
        print("➤ Analyst coverage features encountered an error.")

    # ---------------------------------------------------------
    # 8. NEWS CONTEXT
    # ---------------------------------------------------------
    print("\n[8] NEWS ARTICLES")
    print("-" * 60)
    news = stock.news
    print(f"➤ Recent News Articles Fetched: {len(news)}")
    if news:
        for i, item in enumerate(news[:2]): # Just show top 2
            # Yahoo's news JSON structure can vary, handle safely
            title = item.get('content', {}).get('title') or item.get('title', 'No Title')
            publisher = item.get('content', {}).get('provider', {}).get('displayName') or item.get('publisher', 'Unknown')
            print(f"    {i+1}. [{publisher}] {title}")

    print("\n" + "=" * 80)
    print("✅ CAPABILITIES RADAR SWEEP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    # Test with a highly capitalized, data-rich stock to see maximum capabilities
    run_capabilities_radar("MSFT")
    
    # You can uncomment the line below to test a smaller/international stock 
    # and see how yfinance gracefully handles missing data (e.g. no options or missing financials)
    # run_capabilities_radar("SAN.MC") # Banco Santander (Spain)