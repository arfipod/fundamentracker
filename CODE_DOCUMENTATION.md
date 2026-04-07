# 📖 Code Documentation: FundamenTracker Engine

This document provides technical details on the internal logic, data processing, and automation architecture of the FundamenTracker system.

---

## 1. System Architecture

The system is designed as a **serverless observer**. Due to the limitations of free-tier cloud hosting platforms like PythonAnywhere (which lack scheduled tasks for free accounts), the system uses **GitHub Actions** as the primary execution engine.

* **Trigger:** GitHub Cron Schedule (Every 15 minutes).
* **Environment:** Ubuntu Linux Virtual Machine (Ephemeral).
* **Data Source:** Yahoo Finance API (via `yfinance`).
* **Output:** Telegram Bot API (JSON POST requests).

---

## 2. Data Processing Logic

### 2.1 The "London Penny" Adjustment (GBp vs GBP)
A core feature of the engine is the automatic currency normalization for the London Stock Exchange.
* **Problem:** UK stocks (e.g., `AUTO.L`) have prices quoted in **Pence (GBp)** but earnings (EPS) reported in **Pounds (GBP)**.
* **Logic:**
    ```python
    if currency == 'GBp':
        calculation_price = current_price / 100
    ```
This ensures valuation ratios like P/E are not inflated by a factor of 100.

### 2.2 Manual ROIC Calculation
To solve the issue of missing ROIC data in standard APIs, the engine performs a "Full-Statement Drilldown":
1.  **NOPAT Extraction:** `EBIT * (1 - Effective Tax Rate)`.
2.  **Invested Capital Extraction:** `Total Debt + Shareholders' Equity - Excess Cash`.
3.  **Result:** `ROIC = NOPAT / Invested Capital`.
*Note: For financial institutions (Banks/Insurance), this metric is often bypassed as their balance sheet structure makes ROIC non-comparable.*

---

## 3. Module Breakdown

### `main.py`
The primary entry point. It iterates through the `watchlist` dictionary.
* **`send_telegram_alert(message)`:** Encapsulates the `requests.post` logic. It uses `parse_mode="Markdown"` to allow bolding and emojis in alerts.
* **Error Handling:** Every ticker is wrapped in a `try-except` block. If one ticker fails (e.g., 404 error), the rest of the portfolio continues to be processed.

### `workflow.yml`
Defines the cloud environment.
* **Cron Job:** Set to `*/15 * * * *` (standard crontab syntax for every 15 minutes).
* **Environment Injection:** Maps GitHub Secrets directly to Python OS environment variables using the `env:` block.

---

## 4. Environment Variables

The code requires the following secrets to be configured in the repository settings:

| Variable | Description | Source |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | The unique API key for the bot. | Telegram @BotFather |
| `TELEGRAM_CHAT_ID` | Your numeric personal ID. | Telegram @userinfobot |

---

## 5. Troubleshooting & Limitations

* **API Rate Limiting:** Yahoo Finance may occasionally throttle requests if the watchlist becomes excessively large (e.g., >200 tickers).
* **Cron Precision:** GitHub Actions cron jobs can be delayed by 1-5 minutes during peak server load.
* **Data Latency:** While the script runs every 15 minutes, the underlying data provided by Yahoo Finance may have a standard 15-minute delay depending on the exchange.