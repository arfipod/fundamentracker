from __future__ import annotations

import os
from typing import Any


class GenAILibraryNotInstalledError(Exception):
    pass


class GeminiApiKeyNotConfiguredError(Exception):
    pass


def generate_ai_valuation(market_data_service: Any, ticker: str) -> dict[str, str]:
    try:
        from google import genai
    except ImportError as exc:
        raise GenAILibraryNotInstalledError("Google GenAI library not installed") from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiApiKeyNotConfiguredError(
            "GEMINI_API_KEY not configured. Please set it in your environment."
        )

    client = genai.Client(api_key=api_key)
    symbol = ticker.upper()
    info = market_data_service.get_quote(symbol)

    stats_str = f"Company: {info.get('longName', symbol)}\n"
    stats_str += f"Sector: {info.get('sector', 'N/A')}\n"
    stats_str += f"Industry: {info.get('industry', 'N/A')}\n"
    stats_str += f"Current Price: {info.get('currentPrice', 'N/A')}\n"
    stats_str += f"Trailing P/E: {info.get('trailingPE', 'N/A')}\n"
    stats_str += f"Forward P/E: {info.get('forwardPE', 'N/A')}\n"
    stats_str += f"Price to Book: {info.get('priceToBook', 'N/A')}\n"
    stats_str += f"Return on Equity: {info.get('returnOnEquity', 'N/A')}\n"
    stats_str += f"Debt to Equity: {info.get('debtToEquity', 'N/A')}\n"
    stats_str += f"Profit Margin: {info.get('profitMargins', 'N/A')}\n"
    stats_str += f"Dividend Yield: {info.get('dividendYield', 'N/A')}\n"

    prompt = (
        f"You are a financial analyst. Based on the following current fundamental data for {symbol}:\n\n"
        f"{stats_str}\n\n"
        "Provide a concise (3-4 sentences) valuation analysis. Is the stock undervalued, "
        "fairly valued, or overvalued compared to historical norms and its sector? Be objective."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return {"analysis": response.text}
