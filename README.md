# 📈 FundamenTracker

FundamenTracker is a lightweight automation bot that tracks stock fundamentals and sends Telegram alerts when configurable conditions are met.

The app is designed to run on a schedule (for example, GitHub Actions cron), and persists state in JSONBin.

## What it does

- Receives Telegram bot commands to manage a watchlist and alert rules.
- Supports CLI actions for CI workflows (`add` / `remove` / `alerts`).
- Reads market fundamentals from Yahoo Finance (`yfinance`).
- Sends alerts only on state transitions (prevents duplicate spam while a condition stays true).
- Supports multiple metrics and operators per ticker.

## Project structure

- `src/main.py` — entrypoint/orchestration (CLI mode, Telegram mode, scan mode).
- `src/config.py` — supported metric and operator mappings.
- `src/telegram_service.py` — Telegram API helpers + command parsing.
- `src/watchlist.py` — add/remove/list utilities and metric/target parsing.
- `src/scanner.py` — metric scan + trigger transition logic.
- `src/jsonbin.py` — load/save state from JSONBin.
- `src/state.py` — default state and state-shape guard.
- `client.py` — optional local interactive CLI client for manual state management.

## Required environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes (bot mode) | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes (bot mode) | Chat ID where messages are sent |
| `JSONBIN_ID` | Yes | JSONBin document id |
| `JSONBIN_KEY` | Yes | JSONBin master key |

## State schema

```json
{
  "watchlist": {
    "AAPL": {
      "name": "Apple Inc.",
      "alerts": [
        {
          "metric": "pe",
          "operator": "<",
          "target": 20.0,
          "is_triggered": false
        }
      ]
    }
  },
  "last_update_id": 0
}
```

## Supported metrics

- `pe` → `trailingPE`
- `fpe` → `forwardPE`
- `pb` → `priceToBook`
- `evebitda` → `enterpriseToEbitda`
- `roe` → `returnOnEquity`
- `price` → `currentPrice`

## Supported operators

- `<`, `>`, `<=`, `>=`, `==`, `=`, `!=`

## Telegram commands

- `/add TICKER VALUE` — Adds an alert using defaults: `pe < VALUE`.
- `/add TICKER METRIC OP VALUE` — Adds an alert with explicit metric/operator.
- `/remove TICKER` — Removes a ticker (and all alerts under it).
- `/list` — Lists watchlist entries and current metric values.
- `/alerts` — Lists alert configuration and current trigger status.
- `/state` — Shows the full raw state object.
- `/resetstate` — Clears the watchlist and resets update offset.
- `/help` — Shows available commands.

## CLI usage

```bash
python src/main.py --cli --action add --ticker AAPL --metric pe --operator "<" --value 20
python src/main.py --cli --action add --ticker TSLA --metric price --operator ">" --value 300
python src/main.py --cli --action remove --ticker AAPL
python src/main.py --cli --action alerts
```

You can omit `--metric` and `--operator` on add; defaults are `pe` and `<`.

## Test connectivity mode

```bash
python src/main.py --test
```

Sends a test Telegram message and exits.

## Automation idea (GitHub Actions)

Run periodically with cron and inject required environment variables as secrets.

```yaml
on:
  schedule:
    - cron: "0 * * * *"   # hourly
```

## Notes

- Metric values are fetched live from Yahoo Finance and may be missing for some tickers.
- Trigger thresholds are numeric and may be negative (for metrics where that is meaningful).
- If an alert condition becomes true, one alert is sent and `is_triggered` is set to `true`.
- An alert can fire again only after the condition becomes false at least once.
