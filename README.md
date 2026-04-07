# 📈 FundamenTracker

FundamenTracker is a lightweight automation bot that tracks a watchlist of stocks and sends Telegram alerts when each stock's `trailingPE` drops below a configured trigger.

The app is designed to run on a schedule (for example, GitHub Actions cron), and persists state in JSONBin.

## What it does

- Receives Telegram bot commands to manage a watchlist.
- Supports CLI actions for CI workflows (`add`/`remove`).
- Reads market fundamentals from Yahoo Finance (`yfinance`).
- Sends a Telegram alert only when crossing below the trigger (prevents repeated spam).

## Project structure

- `src/main.py` — entrypoint/orchestration (CLI mode, Telegram mode, scan mode).
- `src/telegram_service.py` — Telegram API helpers + command parsing.
- `src/watchlist.py` — add/remove/list utilities and PE trigger validation.
- `src/scanner.py` — P/E scan + alert transition logic.
- `src/jsonbin.py` — load/save state from JSONBin.
- `src/state.py` — default state and state-shape guard.

## Required environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Chat ID where messages are sent |
| `JSONBIN_ID` | Yes | JSONBin document id |
| `JSONBIN_KEY` | Yes | JSONBin master key |

## State schema

```json
{
  "watchlist": {
    "AAPL": {
      "name": "Apple Inc.",
      "pe_trigger": 20.0,
      "last_pe_alert": null
    }
  },
  "last_update_id": 0
}
```

## Telegram commands

- `/add TICKER PE` — Adds a ticker to the watchlist with a PE trigger threshold.
- `/remove TICKER` — Removes a ticker from the watchlist.
- `/list` — Lists all watched tickers with their PE trigger and current PE value.
- `/alerts` — Lists alert configuration with PE triggers, current PE values, and trigger status.
- `/state` — Shows the full raw state object.
- `/resetstate` — Clears the watchlist and resets the state.
- `/help` — Shows available commands.

## CLI usage

```bash
python src/main.py --cli --action add --ticker AAPL --value 20
python src/main.py --cli --action remove --ticker AAPL
```

## Automation idea (GitHub Actions)

Run periodically with cron and inject the four required environment variables as secrets.

The `cron` syntax is

```# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday; 7 is also Sunday on some systems)
# │ │ │ │ │ │
# │ │ │ │ │ │
# * * * * *  command to execute
```

For instance, to run at the top of every hour:

```yaml
on:
  schedule:
    - cron: "0 * * * *"
``` 

or to run every 15 minutes:

```yaml
on:
  schedule:
    - cron: "* */15 * * *"
``` 


## Notes

- Alerting uses `trailingPE` and `currentPrice` from `yfinance`.
- If a ticker has no `trailingPE`, it is skipped in that run.
- Exceptions per ticker are logged and do not stop scanning of remaining tickers.
- `/list` and `/alerts` commands now display the current PE value for each ticker alongside the configured trigger threshold.
