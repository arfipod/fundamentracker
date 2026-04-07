# 📈 FundamenTracker

**FundamenTracker** is an automated fundamental analysis engine designed to monitor global stock portfolios. It extracts real-time financial data, calculates advanced valuation multiples (including manual ROIC), and sends instant alerts via Telegram when specific value thresholds are hit.

## 🚀 Core Features

* **Global Market Coverage:** Built-in support for US, European, Asian, and Australian markets, with automatic currency handling (including the London GBp/GBP anomaly).
* **Deep Valuation Metrics:** Real-time tracking of P/E, P/FCF, EV/EBITDA, P/S, and P/B ratios.
* **Profitability Scanner:** Monitors ROA, ROE, and all major margins (Gross, Operating, Net).
* **Manual ROIC Calculation:** A custom engine that calculates Return on Invested Capital (NOPAT / Invested Capital) directly from financial statements to ensure 100% data reliability.
* **Smart Ticker Search:** Integrated utility to find exact Yahoo Finance symbols using an internal autocomplete API.

## 🧠 Financial Insights & Lessons Learned

During development, several critical financial "gotchas" were identified and solved:
* **London Exchange Pricing:** UK stocks (like `AUTO.L`) trade in pence (GBp) while financials are in pounds. The system automatically adjusts the price by 100 to keep P/E ratios accurate.
* **Banking & Insurance Ratios:** Traditional metrics like EV/EBITDA and Gross Margins are often `NaN` for financial institutions because their debt is part of their operations.
* **Negative Equity:** High-quality companies with massive buybacks (e.g., VeriSign) can show negative P/B ratios.
* **P/FCF Alerts:** Negative Free Cash Flow multiples indicate a company is currently "burning" cash or investing heavily in CAPEX.

## ☁️ Cloud Automation Architecture

While free-tier cloud platforms like PythonAnywhere lack the necessary scheduling and internet access for this project, FundamenTracker utilizes **GitHub Actions** for 100% free, 24/7 automation.

* **Scheduler:** Runs every 15 minutes via GitHub cron jobs.
* **Security:** All API tokens and Chat IDs are stored in **GitHub Secrets** to prevent exposure in public repositories.
* **Alerting:** Integrated Telegram Bot API for instant valuation notifications.

## 🛠️ Setup Instructions

### 1. Configure the Telegram Bot
* Search for `@BotFather` on Telegram and use `/newbot` to get your **API Token**.
* Message `@userinfobot` to get your unique **Chat ID**.

### 2. Set Up GitHub Secrets
Go to your repository **Settings > Secrets and variables > Actions** and add:
* `TELEGRAM_TOKEN`: Your bot's API token.
* `TELEGRAM_CHAT_ID`: Your personal numeric chat ID.

### 3. Deploy
1.  Push the `.github/workflows/main.yml` file to your repo.
2.  Push your `src/main.py` script containing the watchlist and alert logic.
3.  The system will now run automatically every 15 minutes.

## 📚 Documentation

For detailed technical information on the internal logic, data processing, and architecture, please refer to the [Code Documentation](CODE_DOCUMENTATION.md).