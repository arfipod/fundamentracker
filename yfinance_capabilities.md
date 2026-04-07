# 📊 yfinance Capabilities & Financial Logic Reference

This document serves as a technical reference for the `yfinance` library methods and the custom financial logic implemented in the **FundamenTracker** project.

---

## 🛠️ Core Object: `yf.Ticker`

The primary way to interact with data is by initializing a `Ticker` object:
```python
import yfinance as yf
stock = yf.Ticker("AAPL")
```

### 📋 The .info Dictionary: Key Attributes
The `.info` attribute is the most powerful tool for real-time fundamental data. It returns a dictionary containing over 150 data points.

#### 1. Real-Time Pricing & Identity
* **currentPrice:** The latest traded price.
* **currency:** The currency the stock is traded in (e.g., USD, EUR, GBp).
* **symbol / shortName:** Ticker symbol and the company's common name.
* **quoteType:** Identifies if the instrument is an EQUITY or ETF.

#### 2. Valuation Multiples
* **trailingPE:** Price-to-Earnings ratio based on the last 12 months.
* **forwardPE:** P/E based on analyst projections for the next year.
* **enterpriseToEbitda:** EV/EBITDA multiple (crucial for capital-intensive industries).
* **priceToBook:** P/B ratio.
* **priceToSalesTrailing12Months:** P/S ratio.

#### 3. Profitability & Efficiency
* **returnOnAssets (ROA):** Net Income / Total Assets.
* **returnOnEquity (ROE):** Net Income / Shareholders' Equity.
* **grossMargins:** Percentage of revenue exceeding Cost of Goods Sold.
* **operatingMargins:** Operating income as a percentage of revenue.

### 📈 Deep Financial Data (Pandas DataFrames)
For manual calculations (like ROIC), yfinance provides full financial statements.
* `stock.financials`: Annual Income Statement.
* `stock.balance_sheet`: Annual Balance Sheet.
* `stock.cashflow`: Annual Cash Flow Statement.

### 💡 Specialized Financial Logic (Advanced Discoveries)

#### 1. The London Exchange Pricing Fix
UK stocks trade in Pence (GBp) but report in Pounds (GBP).
* **Solution:** If `currency == 'GBp'`, divide the `currentPrice` by 100 before calculating valuation multiples.

#### 2. Handling Missing Industry Data
* **Financial Institutions (Banks/Insurance):** Often return `None` or `NaN` for Gross Margin and EV/EBITDA because their debt is an operational tool rather than traditional financing.
* **High-Growth/Loss-Making:** P/E will be `None` if Earnings per Share (EPS) is negative.

#### 3. Manual ROIC Logic
When yfinance does not provide ROIC directly, we use:
* **NOPAT:** EBIT * (1 - Tax Rate) from `.financials`.
* **Invested Capital:** Total Debt + Equity - Excess Cash from `.balance_sheet`.

### 🔍 Smart Ticker Discovery
While not part of the yfinance library, we discovered that the Yahoo Finance internal search API is essential for finding exact tickers for European exchanges (e.g., NOVO-B.CO vs NVO).
* **Endpoint:** `https://query2.finance.yahoo.com/v1/finance/search?q={query}`
