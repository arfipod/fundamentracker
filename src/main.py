import yfinance as yf
import pandas as pd
import os
import requests
import numpy as np
import sys  # Added to handle command-line arguments

# Securely load credentials from Environment Variables
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# If you run: python main.py --test
if len(sys.argv) > 1 and sys.argv[1] == "--test":
    print("Running connection test...")
    test_msg = "🚀 *FundamenTracker Test*: Your GitHub Action is connected successfully!"
    send_telegram_alert(test_msg)
    print("Test message sent. Exiting.")
    sys.exit(0)  # Stop execution here during a test

# Your watchlist (You can expand this as needed)
watchlist = [
    {'ticker': 'AAPL', 'name': 'Apple'},
    {'ticker': 'TSLA', 'name': 'Tesla'},
    {'ticker': 'NVO',  'name': 'Novo Nordisk'}
]

print("Starting 15-minute fundamental scan...")

for item in watchlist:
    ticker = item['ticker']
    try:
        data = yf.Ticker(ticker).info
        price = data.get('currentPrice')
        pe = data.get('trailingPE')
        
        # Example Alert Condition: If P/E falls below 25
        if pe and pe < 25:
            msg = f"🚨 *VALUATION ALERT* 🚨\n\n" \
                  f"The company *{item['name']}* ({ticker}) now has a P/E of *{pe:.2f}*.\n" \
                  f"Current Price: ${price}"
            send_telegram_alert(msg)
            print(f"Alert sent for {ticker}")
        
    except Exception as e:
        print(f"Error processing {ticker}: {e}")

print("Scan completed.")