import yfinance as yf
import pandas as pd

def extract_critical_dates(ticker_symbol="AAPL"):
    print("-" * 70)
    print(f"📅 EXTRACTING CALENDAR AND KEY DATES FOR: {ticker_symbol}")
    print("-" * 70)
    
    stock = yf.Ticker(ticker_symbol)
    
    # ---------------------------------------------------------
    # 1. THE QUICK CALENDAR (UPCOMING EVENTS)
    # ---------------------------------------------------------
    print("\n[1] UPCOMING EVENTS (stock.calendar)")
    try:
        calendar = stock.calendar
        # FIX 1: Safely handle standard Python dictionaries instead of DataFrames
        if isinstance(calendar, dict) and calendar:
            for event, date_info in calendar.items():
                print(f"  ➤ {event}: {date_info}")
        else:
            print("  ➤ No upcoming events scheduled in the general calendar.")
    except Exception as e:
        print(f"  ❌ Error reading calendar: {e}")

    # ---------------------------------------------------------
    # 2. EARNINGS HISTORY (PREVIOUS AND NEXT)
    # ---------------------------------------------------------
    print("\n[2] EARNINGS DATES (stock.get_earnings_dates)")
    try:
        # Extract the last 10 dates (future and past)
        earnings = stock.get_earnings_dates(limit=10)
        
        if earnings is not None and not earnings.empty:
            # FIX 2: Updated Pandas syntax to avoid the deprecation warning
            now = pd.Timestamp.now('UTC')
            
            # Use Pandas to filter and separate the past from the future
            future_earnings = earnings[earnings.index > now].sort_index(ascending=True)
            past_earnings = earnings[earnings.index <= now].sort_index(ascending=False)
            
            # Extract the next date
            if not future_earnings.empty:
                next_date = future_earnings.index[0]
                print(f"  🟢 NEXT EARNINGS: {next_date.strftime('%B %d, %Y')}")
            else:
                print("  🟢 NEXT EARNINGS: Date not yet officially announced.")
                
            # Extract the previous date
            if not past_earnings.empty:
                prev_date = past_earnings.index[0]
                print(f"  🔵 LAST EARNINGS: {prev_date.strftime('%B %d, %Y')}")
                
                # Extract the EPS Surprise
                last_surprise = past_earnings['Surprise(%)'].iloc[0]
                print(f"      ↳ EPS Surprise: {last_surprise * 100:.2f}%")
                
        else:
             print("  ➤ No earnings dates found.")
    except ImportError:
        print("  ❌ ERROR: Failed to read earnings. Make sure to run: pip install lxml")
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        
    print("-" * 70)

if __name__ == "__main__":
    extract_critical_dates("COST")