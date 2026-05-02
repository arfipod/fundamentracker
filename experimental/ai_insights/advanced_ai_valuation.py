import os
import json
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load the specific .env file before anything else
load_dotenv('/home/arfipod/git/fundamentracker/.env')

def safe_extract_to_csv(df, rows_to_extract):
    """
    Safely extracts specific accounting rows from a yfinance DataFrame,
    formats the dates to years, and returns a CSV string for the AI.
    """
    if df is None or df.empty:
        return "Data not available."
    
    try:
        # Find which requested rows actually exist in the dataframe
        available_rows = [row for row in rows_to_extract if row in df.index]
        if not available_rows:
            return "Specific accounting metrics not found."
            
        sub_df = df.loc[available_rows].copy()
        
        # Convert datetime columns to simple 'YYYY' strings for cleaner AI context
        sub_df.columns = [str(col)[:4] if isinstance(col, pd.Timestamp) else str(col) for col in sub_df.columns]
        
        # Return as CSV format (LLMs read CSV perfectly and it uses fewer tokens than JSON)
        return sub_df.to_csv()
    except Exception as e:
        return f"Error formatting data: {e}"

def test_deep_institutional_valuation(ticker_symbol="AAPL"):
    print("-" * 80)
    print(f"📊 1. Fetching DEEP accounting tables for {ticker_symbol}...")
    
    stock = yf.Ticker(ticker_symbol)
    
    # --- 1. EXTRACT RAW FINANCIAL TABLES ---
    
    # A. Income Statement (Growth & Margins)
    income_metrics = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
    income_csv = safe_extract_to_csv(stock.financials, income_metrics)
    
    # B. Cash Flow Statement (The Terry Smith Reality Check)
    # Different companies report these with slightly different names, we try the most common ones
    cashflow_metrics = ['Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow']
    cashflow_csv = safe_extract_to_csv(stock.cashflow, cashflow_metrics)
    
    # C. Insider Activity (Skin in the game)
    insider_context = "No insider data available."
    try:
        insiders = stock.insider_purchases
        if insiders is not None and not insiders.empty:
            # Just grab the first few rows of summary data
            insider_context = insiders.head(3).to_csv(index=False)
    except:
        pass
        
    # D. Current Valuation Context
    info = stock.info
    trailing_pe = info.get('trailingPE', 'N/A')
    forward_pe = info.get('forwardPE', 'N/A')

    print("\n   [Data Successfully Extracted & Formatted for AI]")
    print(f"   ➤ Income Statement Rows: {income_metrics}")
    print(f"   ➤ Cash Flow Rows:        {cashflow_metrics}")
    print(f"   ➤ Current Valuation:     PE: {trailing_pe} | Fwd PE: {forward_pe}")
    print("-" * 80)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is missing.")
        return

    model_name = 'gemini-flash-latest' 
    print(f"🧠 2. Running Deep Institutional Analysis using [{model_name}]...")
    
    client = genai.Client()
    
    # --- 2. THE ADVANCED PROMPT ---
    prompt = f"""
    Act as a rigorous, Warren Buffett and Terry Smith-style fundamental financial analyst evaluating {ticker_symbol}.
    You are being provided with RAW, historical accounting data (in CSV format) spanning the last 4 years.
    
    [4-YEAR INCOME STATEMENT TRENDS]
    {income_csv}
    
    [4-YEAR CASH FLOW TRENDS]
    {cashflow_csv}
    
    [CURRENT VALUATION & INSIDER ACTIVITY]
    * Trailing PE: {trailing_pe}
    * Forward PE: {forward_pe}
    * Recent Insider Purchases: 
    {insider_context}
    
    Task: Provide a holistic evaluation of {ticker_symbol} focusing on TRENDS, not just current snapshots.
    1. Calculate Gross Margins (Gross Profit / Revenue) across the years. Is the moat expanding or shrinking?
    2. Analyze Earnings Quality by comparing Free Cash Flow to Net Income. Are their earnings real cash?
    3. Determine if the current PE ratio is justified by the trajectory of their cash generation.
    4. Consider if insiders are buying or selling to gauge management confidence.
    """
    
    try:
        # --- 3. JSON SCHEMA ENFORCEMENT ---
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1, # Extremely low temperature for strict financial accuracy
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "moat_trend": {
                            "type": "STRING",
                            "enum": ["Expanding", "Stable", "Deteriorating", "Unclear"],
                            "description": "Verdict on the economic moat based on the 4-year Gross Margin and Revenue trends."
                        },
                        "earnings_quality": {
                            "type": "STRING",
                            "enum": ["High (FCF > Net Income)", "Medium", "Low (Red Flag)"],
                            "description": "Verdict on whether reported net income translates to actual free cash flow."
                        },
                        "sentiment": {
                            "type": "STRING",
                            "enum": ["🟢 Undervalued / Strong Buy", "🟡 Fair Value / Hold", "🔴 Overvalued / Value Trap"],
                            "description": "Overall verdict."
                        },
                        "deep_insights": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Exactly 5 rigorous, data-backed bullet points (max 25 words each). Cite specific margin percentages or cash flow figures from the CSV data provided."
                        }
                    },
                    "required": ["moat_trend", "earnings_quality", "sentiment", "deep_insights"]
                }
            )
        )
        
        # --- 4. PARSE AND DISPLAY ---
        result = json.loads(response.text)
        
        print("\n✅ DEEP ANALYSIS RECEIVED!\n")
        print(f"Moat Trend:       {result.get('moat_trend')}")
        print(f"Earnings Quality: {result.get('earnings_quality')}")
        print(f"Overall Verdict:  {result.get('sentiment')}\n")
        
        print("Key Institutional Insights:")
        for i, insight in enumerate(result.get('deep_insights', []), 1):
            print(f"  {i}. {insight}")
            
    except Exception as e:
        print(f"\n❌ An error occurred with the AI: {e}")
    print("-" * 80)

if __name__ == "__main__":
    print("\n>>> INITIALIZING DEEP INSTITUTIONAL SCAN <<<")
    test_deep_institutional_valuation("MSFT")