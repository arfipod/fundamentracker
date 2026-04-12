import os
import sys
import yfinance as yf
from dotenv import load_dotenv

# Load env variables from .env BEFORE any intra-project imports occur
load_dotenv()

# Add src to sys.path so we can import the project modules easily
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config import METRICS_MAP, OPERATORS_MAP
from jsonbin import load_state, save_state
from state import ensure_state_shape
from watchlist import add_ticker, remove_ticker, format_watchlist_message, format_alerts_message

def print_menu():
    print("\n" + "="*40)
    print("📈 FundamenTracker CLI Client")
    print("="*40)
    print("1. List Watchlist")
    print("2. List Alerts Status")
    print("3. Add Alert")
    print("4. Remove Ticker")
    print("5. View Supported Metrics & Operators")
    print("6. Test/Inspect Ticker on Yahoo Finance")
    print("7. Exit")
    print("="*40)

def main():
    # Check if variables are set
    if not os.getenv("JSONBIN_ID") or not os.getenv("JSONBIN_KEY"):
        print("⚠️ Warning: JSONBIN_ID or JSONBIN_KEY not found in environment or .env file.")
        print("Data might not be loaded or saved correctly.")

    
    print("Loading state from JSONBin...")
    state = ensure_state_shape(load_state())
    print("State loaded successfully!")

    while True:
        print_menu()
        choice = input("Select an option (1-7): ").strip()

        if choice == "1":
            print("\n" + format_watchlist_message(state))
            
        elif choice == "2":
            print("\n" + format_alerts_message(state))
            
        elif choice == "3":
            ticker = input("Enter Ticker (e.g., AAPL): ").strip().upper()
            if not ticker:
                continue
                
            print(f"Available metrics: {', '.join(METRICS_MAP.keys())}")
            metric = input("Enter Metric: ").strip().lower()
            if metric not in METRICS_MAP:
                print("❌ Invalid metric.")
                continue
                
            print(f"Available operators: {', '.join(OPERATORS_MAP.keys())}")
            op = input("Enter Operator: ").strip()
            if op not in OPERATORS_MAP:
                print("❌ Invalid operator.")
                continue
                
            try:
                target = float(input("Enter Target Value: ").strip())
            except ValueError:
                print("❌ Target must be a number.")
                continue

            print(f"Adding {ticker} with {metric} {op} {target}...")
            symbol, name = add_ticker(state, ticker, metric, op, target)
            save_state(state)
            print(f"✅ Added {name} ({symbol}) with {metric} {op} {target}")

        elif choice == "4":
            ticker = input("Enter Ticker to remove: ").strip().upper()
            if not ticker:
                continue
            removed, symbol = remove_ticker(state, ticker)
            if removed:
                save_state(state)
                print(f"🗑️ Removed {symbol}")
            else:
                print("❌ Ticker not found in watchlist.")

        elif choice == "5":
            print("\n📌 Supported Metrics:")
            for m_key, yf_key in METRICS_MAP.items():
                print(f"  - {m_key} (maps to '{yf_key}')")
            
            print("\n📌 Supported Operators:")
            print(f"  {', '.join(OPERATORS_MAP.keys())}")

        elif choice == "6":
            ticker = input("Enter Ticker to inspect: ").strip().upper()
            if not ticker:
                continue
                
            print(f"Fetching data for '{ticker}' from Yahoo Finance...")
            try:
                info = yf.Ticker(ticker).info
                name = info.get("shortName", "N/A")
                price = info.get("currentPrice", "N/A")
                
                print(f"\n📊 {name} ({ticker})")
                print(f"Current Price: {price}")
                print("-" * 20)
                print("Available config metrics for this ticker:")
                
                for m_key, yf_key in METRICS_MAP.items():
                    val = info.get(yf_key)
                    if val is not None:
                        print(f"  ✅ {m_key}: {val}")
                    else:
                        print(f"  ❌ {m_key}: Not available from YF")
                        
            except Exception as e:
                print(f"❌ Error fetching data: {e}")

        elif choice == "7":
            print("Exiting. Goodbye!")
            break
            
        else:
            print("❌ Invalid option. Please select a number from 1 to 7.")

if __name__ == "__main__":
    main()
