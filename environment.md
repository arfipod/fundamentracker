# Python Environment Management Guide

This guide explains how to set up and use a local Python virtual environment for FundamenTracker.

## 1) Create a virtual environment

```bash
python3 -m venv .venv
```

## 2) Activate the environment

```bash
source .venv/bin/activate
```

Or use the helper script (must be sourced, not executed):

```bash
source activate_env.sh
```

## 3) Install dependencies

```bash
pip install -r requirements.txt
```

## 4) Configure environment variables

Set these before running the app:

- `JSONBIN_ID`
- `JSONBIN_KEY`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

You can export them in your shell or place them in a `.env` file.

> Note: `client.py` explicitly loads `.env` using `python-dotenv`. `src/main.py` reads variables directly from the process environment.

## 5) Run the project

### Bot/scan entrypoint

```bash
python src/main.py
```

### One-off CLI actions

```bash
python src/main.py --cli --action add --ticker AAPL --metric pe --operator "<" --value 20
python src/main.py --cli --action remove --ticker AAPL
python src/main.py --cli --action alerts
```

### Telegram connectivity test

```bash
python src/main.py --test
```

### Optional local menu client

```bash
python client.py
```

## 6) Run tests

```bash
pytest
```

`pytest.ini` already sets `pythonpath = src`.

## 7) Deactivate

```bash
deactivate
```

## Quick Git hygiene

- Do not commit `.venv/`.
- Update `requirements.txt` when dependencies change.
