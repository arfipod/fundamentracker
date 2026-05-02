import os
import json
import yfinance as yf
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

def test_stock_valuation_insights(ticker_symbol="AAPL", use_pro=False):
    print("-" * 70)
    print(f"📊 1. Fetching deep fundamental data and news for {ticker_symbol}...")
    
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    # --- 1. THE FUNDAMENTAL DASHBOARD ---
    
    # A. Valuation
    trailing_pe = info.get('trailingPE', 'N/A')
    forward_pe = info.get('forwardPE', 'N/A')
    peg_ratio = info.get('pegRatio', 'N/A')
    price_to_book = info.get('priceToBook', 'N/A')
    
    # B. Growth (YoY)
    revenue_growth = format_percent(info.get('revenueGrowth', 'N/A'))
    earnings_growth = format_percent(info.get('earningsGrowth', 'N/A'))
    
    # C. Profitability & Capital Efficiency (ROIC Proxies)
    operating_margin = format_percent(info.get('operatingMargins', 'N/A'))
    profit_margin = format_percent(info.get('profitMargins', 'N/A'))
    roe = format_percent(info.get('returnOnEquity', 'N/A'))
    roa = format_percent(info.get('returnOnAssets', 'N/A'))
    roc = format_percent(info.get('returnOnCapital', 'N/A'))
    
    # D. Financial Health
    debt_to_equity = info.get('debtToEquity', 'N/A')

    # Print the dashboard to console for developer visibility
    print("\n   [Valuation]")
    print(f"   ➤ Trailing PE:  {trailing_pe} | Forward PE: {forward_pe}")
    print(f"   ➤ PEG Ratio:    {peg_ratio} | Price/Book: {price_to_book}")
    
    print("\n   [Growth (YoY)]")
    print(f"   ➤ Revenue:      {revenue_growth} | Earnings: {earnings_growth}")
    
    print("\n   [Profitability & Capital Efficiency]")
    print(f"   ➤ Oper. Margin: {operating_margin} | Net Margin: {profit_margin}")
    print(f"   ➤ ROE:          {roe} | ROA: {roa} | ROC: {roc}")
    
    print("\n   [Health]")
    print(f"   ➤ Debt/Equity:  {debt_to_equity}")
    
    # --- 2. THE CONTEXT (News) ---
    news_items = stock.news
    news_context_list = []
    
    for item in news_items[:8]: 
        if 'content' in item and 'title' in item['content']:
            title = item['content']['title']
            summary = item['content'].get('summary', 'No summary provided.')
            news_entry = f"Headline: {title}\nSummary: {summary}\n"
            news_context_list.append(news_entry)
            
    news_context_list = news_context_list[:4] if news_context_list else ["No recent news available."]
    
    print("\n   📰 Recent News Context (Titles sent to AI):")
    for news in news_context_list:
        print(f"      - {news.split(chr(10))[0]}...") 
    print("-" * 70)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is missing.")
        return

    model_name = 'gemini-2.5-pro' if use_pro else 'gemini-2.5-flash'
    print(f"🧠 2. Requesting holistic AI analysis using [{model_name}]...")
    
    client = genai.Client()
    
    # --- 3. THE PROMPT ---
    full_news_text = "\n".join(news_context_list)
    prompt = f"""
    Act as a rigorous, Warren Buffett and Terry Smith-style fundamental financial analyst evaluating {ticker_symbol}.
    
    [FUNDAMENTAL DATA]
    * Valuation: Trailing PE: {trailing_pe}, Forward PE: {forward_pe}, PEG: {peg_ratio}, P/B: {price_to_book}
    * Growth (YoY): Revenue Growth: {revenue_growth}, Earnings Growth: {earnings_growth}
    * Profitability & Capital Efficiency: Oper Margin: {operating_margin}, Net Margin: {profit_margin}, ROE: {roe}, ROA: {roa}, Return on Capital: {roc}
    * Financial Risk: Debt-to-Equity: {debt_to_equity}
    
    [MARKET CONTEXT (News Headlines and Summaries)]
    {full_news_text}
    
    Task: Provide a holistic, institutional-grade evaluation of {ticker_symbol}.
    Crucially, evaluate the company's Capital Allocation Efficiency. Use the ROE, ROA, ROC and Margins as a proxy for ROIC to determine if the company has a strong economic moat.
    Synthesize how this capital efficiency and growth justify (or fail to justify) the current Valuation multiples. 
    If the news directly mentions the company or sector, blend that context into your evaluation. If it's generic, weigh the broader market sentiment. If data is 'N/A', ignore that specific metric.
    """
    
    try:
        # --- 4. JSON SCHEMA ENFORCEMENT ---
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4, 
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "sentiment": {
                            "type": "STRING",
                            "enum": ["🟢 Undervalued / Strong Buy", "🟡 Fair Value / Hold", "🔴 Overvalued / Value Trap"],
                            "description": "Overall fundamental verdict based on efficiency, growth, and price."
                        },
                        "insights": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Exactly 5 rigorous bullet points (max 18 words each). Cross-reference capital efficiency (ROA/ROE/Margins) and growth against the valuation (PE/PEG), factoring in news."
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
    print("-" * 70)

if __name__ == "__main__":
    print("\n>>> TESTING STANDARD SCAN (FLASH) <<<")
    test_stock_valuation_insights("MSFT", use_pro=False)