import pandas as pd
import yfinance as yf
import json
import time
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables (ensure GEMINI_API_KEY is present)[cite: 3, 6]
load_dotenv('/home/arfipod/git/fundamentracker/.env')

def run_ai_augmented_scan(tickers, enable_ai=True):
    """
    Scans a list of tickers and returns a structured DataFrame containing
    company info and 5 AI-generated insights per ticker using Gemini 3 Flash.
    """
    client = genai.Client()
    model_name = 'gemini-flash-latest' # Optimized for high-throughput tasks[cite: 3, 6]
    scan_results = []

    print(f"🚀 Starting scan for {len(tickers)} tickers. AI Enabled: {enable_ai}")

    for ticker in tickers:
        print(f"Processing {ticker}...")
        row_data = {"Ticker": ticker}
        
        try:
            # 1. FETCH DATA (yfinance)[cite: 2, 5, 6]
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract core metrics as used in your existing dashboard logic[cite: 6]
            row_data.update({
                "Company": info.get('longName', 'N/A'),
                "Sector": info.get('sector', 'N/A'),
                "Trailing PE": info.get('trailingPE', 'N/A'),
                "Forward PE": info.get('forwardPE', 'N/A'),
                "P/B Ratio": info.get('priceToBook', 'N/A'),
                "FCF": info.get('freeCashflow', 'N/A'),
                "ROE": info.get('returnOnEquity', 'N/A'),
                "Debt/Equity": info.get('debtToEquity', 'N/A')
            })

            # 2. AI ANALYSIS WITH RETRY LOGIC[cite: 3, 6]
            if enable_ai:
                prompt = f"""
                Act as a Buffett-style analyst. Evaluate {ticker} ({row_data['Company']}).
                Metrics: PE: {row_data['Trailing PE']}, ROE: {row_data['ROE']}, FCF: {row_data['FCF']}.
                Synthesize the valuation against cash generation.
                """
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                temperature=0.1, # Keep it analytical
                                response_mime_type="application/json",
                                response_schema={
                                    "type": "OBJECT",
                                    "properties": {
                                        "sentiment": {"type": "STRING"},
                                        "insights": {
                                            "type": "ARRAY",
                                            "items": {"type": "STRING"},
                                            "description": "Exactly 5 rigorous bullet points." # Schema enforcement[cite: 3, 6]
                                        }
                                    },
                                    "required": ["sentiment", "insights"]
                                }
                            )
                        )
                        
                        ai_data = json.loads(response.text)
                        row_data["AI Verdict"] = ai_data.get("sentiment", "N/A")
                        
                        # Flatten exactly 5 insights into structured columns
                        insights = ai_data.get("insights", [])
                        for i in range(5):
                            row_data[f"Insight_{i+1}"] = insights[i] if i < len(insights) else "N/A"
                        
                        break # Success - exit retry loop
                        
                    except Exception as e:
                        # Handle 503 (Busy) or 429 (Rate Limit) specifically[cite: 6]
                        if ("503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                            wait = 2 ** attempt # Exponential backoff: 1s, 2s, 4s
                            print(f"  ⚠️ Service busy. Retrying {ticker} in {wait}s...")
                            time.sleep(wait)
                        else:
                            print(f"  ❌ AI analysis failed for {ticker}: {e}")
                            row_data["AI Verdict"] = "Service Unavailable"
                            break

            scan_results.append(row_data)
            time.sleep(1) # Safety buffer between tickers[cite: 5]

        except Exception as e:
            print(f"❌ Critical error fetching data for {ticker}: {e}")
            row_data["Error"] = str(e)
            scan_results.append(row_data)

    # 3. CONVERT TO STRUCTURED DATAFRAME
    return pd.DataFrame(scan_results)

if __name__ == "__main__":
    # Test with a mix of symbols[cite: 6]
    test_tickers = ["AAPL", "MSFT", "LMN.V"]
    final_df = run_ai_augmented_scan(test_tickers)
    
    # Display the structured results
    print("\n--- FINAL SCAN RESULTS ---")
    print(final_df.to_string())