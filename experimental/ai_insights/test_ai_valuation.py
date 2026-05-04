import os
import json
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load the specific .env file before anything else
load_dotenv('/home/arfipod/git/fundamentracker/.env')

def format_percent(value):
    """Helper to format decimals as percentages for the AI (e.g., 0.15 -> 15.0%)"""
    if isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    return value

def format_currency(value):
    """Helper to format large numbers into readable billions/millions."""
    if isinstance(value, (int, float)):
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif value >= 1e6:
            return f"${value / 1e6:.2f}M"
        return f"${value:,.2f}"
    return value

def get_3yr_margin_trend(stock):
    """Safely extracts the last 3 years of Gross Margins to check moat consistency."""
    try:
        financials = stock.financials
        if 'Gross Profit' in financials.index and 'Total Revenue' in financials.index:
            gross_profit = financials.loc['Gross Profit'].dropna()
            revenue = financials.loc['Total Revenue'].dropna()
            
            margins = (gross_profit / revenue).dropna()
            # Take the most recent 3 years, reverse to chronological order (Oldest -> Newest)
            recent_margins = margins.head(3)[::-1] 
            
            return " -> ".join([format_percent(m) for m in recent_margins])
    except Exception:
        pass
    return "N/A"

def test_stock_valuation_insights(ticker_symbol="AAPL"):
    print("-" * 80)
    print(f"📊 1. Fetching Buffett/Smith fundamental data for {ticker_symbol}...")
    
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    # --- 1. THE FUNDAMENTAL DASHBOARD ---
    
    # A. Valuation
    trailing_pe = info.get('trailingPE', 'N/A')
    forward_pe = info.get('forwardPE', 'N/A')
    price_to_book = info.get('priceToBook', 'N/A')
    
    # B. Cash Flow Reality (The Terry Smith Check)
    fcf = info.get('freeCashflow', 'N/A')
    net_income = info.get('netIncomeToCommon', 'N/A')
    
    cash_conversion = "N/A"
    if isinstance(fcf, (int, float)) and isinstance(net_income, (int, float)) and net_income > 0:
        cash_conversion = format_percent(fcf / net_income)
        
    # C. Historical Moat Consistency (The Warren Buffett Check)
    historical_margins = get_3yr_margin_trend(stock)
    
    # D. Profitability & Capital Efficiency
    roe = format_percent(info.get('returnOnEquity', 'N/A'))
    roc = format_percent(info.get('returnOnCapital', 'N/A'))
    
    # E. Financial Health
    debt_to_equity = info.get('debtToEquity', 'N/A')

    # Print dashboard to console
    print("\n   [Valuation]")
    print(f"   ➤ Trailing PE:  {trailing_pe} | Forward PE: {forward_pe} | P/B: {price_to_book}")
    
    print("\n   [Cash Flow & Earnings Quality]")
    print(f"   ➤ Free Cash Flow:   {format_currency(fcf)}")
    print(f"   ➤ Net Income:       {format_currency(net_income)}")
    print(f"   ➤ Cash Conversion:  {cash_conversion} (FCF / Net Income)")
    
    print("\n   [Moat & Capital Efficiency]")
    print(f"   ➤ 3-Yr Gross Margin Trend: {historical_margins}")
    print(f"   ➤ ROE: {roe} | ROC: {roc}")
    
    print("\n   [Health]")
    print(f"   ➤ Debt/Equity:  {debt_to_equity}")
    
    # --- 2. THE CONTEXT (News) ---
    news_items = stock.news
    news_context_list = []
    
    for item in news_items[:8]: 
        if 'content' in item and 'title' in item['content']:
            title = item['content']['title']
            summary = item['content'].get('summary', 'No summary provided.')
            news_context_list.append(f"Headline: {title}\nSummary: {summary}\n")
            
    news_context_list = news_context_list[:4] if news_context_list else ["No recent news available."]
    print("-" * 80)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is missing.")
        return

    # Using the best value/performance model alias
    model_name = 'gemini-flash-latest' 
    print(f"🧠 2. Requesting holistic AI analysis using [{model_name}]...")
    
    client = genai.Client()
    
    # --- 3. THE PROMPT ---
    full_news_text = "\n".join(news_context_list)
    prompt = f"""
    Act as a rigorous, Warren Buffett and Terry Smith-style fundamental financial analyst evaluating {ticker_symbol}.
    
    [FUNDAMENTAL DATA]
    * Valuation: Trailing PE: {trailing_pe}, Forward PE: {forward_pe}, P/B: {price_to_book}
    * Cash Flow Reality: Free Cash Flow: {format_currency(fcf)}, Cash Conversion Ratio (FCF/Net Income): {cash_conversion}
    * Moat Consistency: 3-Year Gross Margin Trend (Oldest to Newest): {historical_margins}
    * Capital Efficiency: ROE: {roe}, Return on Capital: {roc}
    * Financial Risk: Debt-to-Equity: {debt_to_equity}
    
    [MARKET CONTEXT (News Headlines and Summaries)]
    {full_news_text}
    
    Task: Provide a holistic, institutional-grade evaluation of {ticker_symbol}.
    Crucially, evaluate the company's Free Cash Flow generation and Moat Consistency. Use the Cash Conversion ratio to determine if earnings are real cash, and the 3-Year Margin Trend to see if the moat is expanding or degrading.
    Synthesize how this cash generation and historical consistency justify (or fail to justify) the current Valuation multiples. 
    If data is 'N/A', ignore that specific metric.
    """
    
    try:
        # --- 4. JSON SCHEMA ENFORCEMENT ---
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, # Lowered slightly for more analytical, less creative outputs
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "sentiment": {
                            "type": "STRING",
                            "enum": ["🟢 Undervalued / Strong Buy", "🟡 Fair Value / Hold", "🔴 Overvalued / Value Trap"],
                            "description": "Overall fundamental verdict based on cash flow, moat consistency, and price."
                        },
                        "insights": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Exactly 5 rigorous bullet points (max 20 words each). Focus heavily on Cash Conversion, Margin trends, and ROE/ROC against the PE valuation."
                        }
                    },
                    "required": ["sentiment", "insights"]
                }
            )
        )
        
        # --- 5. PARSE AND DISPLAY ---
        result = json.loads(response.text)
        
        print("\n✅ Holistic Analysis received successfully!\n")
        print(f"Verdict: {result.get('sentiment')}")
        for i, insight in enumerate(result.get('insights', []), 1):
            print(f"  {i}. {insight}")
            
    except Exception as e:
        print(f"\n❌ An error occurred with the AI: {e}")
    print("-" * 80)

if __name__ == "__main__":
    print("\n>>> TESTING VALUE-PERFORMANCE SCAN <<<")
    test_stock_valuation_insights("LMN.V")