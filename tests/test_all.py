import unittest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from state import ensure_state_shape
from config import METRICS_MAP
from watchlist import add_ticker, format_watchlist_message, format_alerts_message, remove_ticker
from telegram_service import process_telegram_commands
from scanner import run_fundamental_scan

class TestFundamenTracker(unittest.TestCase):
    def test_ensure_state_shape(self):
        state = ensure_state_shape(None)
        self.assertEqual(state, {"watchlist": {}, "last_update_id": 0})
        
        state["watchlist"]["AAPL"] = {"name": "Apple"}
        self.assertEqual(ensure_state_shape(state), state)

    @patch('watchlist.yf.Ticker')
    def test_add_ticker(self, mock_ticker):
        # Setup mock
        mock_info = {"shortName": "Apple Inc.", "trailingPE": 20.0}
        mock_ticker.return_value.info = mock_info

        state = {"watchlist": {}, "last_update_id": 0}
        
        # Test adding alert 1
        symbol, name = add_ticker(state, "AAPL", "pe", "<", 25.0)
        self.assertEqual(symbol, "AAPL")
        self.assertEqual(name, "Apple Inc.")
        self.assertEqual(len(state["watchlist"]["AAPL"]["alerts"]), 1)
        
        # Test adding alert 2
        add_ticker(state, "AAPL", "pe", ">", 10.0)
        self.assertEqual(len(state["watchlist"]["AAPL"]["alerts"]), 2)
        
        # Test remove ticker
        removed, r_sym = remove_ticker(state, "AAPL")
        self.assertTrue(removed)
        self.assertEqual(r_sym, "AAPL")
        self.assertNotIn("AAPL", state["watchlist"])

    @patch('telegram_service.get_updates')
    @patch('telegram_service.send_message')
    @patch('telegram_service.add_ticker')
    def test_telegram_process_commands(self, mock_add_ticker, mock_send_message, mock_get_updates):
        state = {"watchlist": {}, "last_update_id": 100}
        # Simulate new telegram messages
        mock_get_updates.return_value = [
            {"update_id": 101, "message": {"text": "/add TSLA 15"}},
            {"update_id": 102, "message": {"text": "/add MSFT price > 300"}},
            {"update_id": 103, "message": {"text": "/list"}}
        ]
        
        mock_add_ticker.side_effect = [("TSLA", "Tesla Inc."), ("MSFT", "Microsoft Corp.")]
        
        new_state = process_telegram_commands(state, None, "http://api", "chat_id")
        
        self.assertEqual(new_state["last_update_id"], 103)
        self.assertEqual(mock_add_ticker.call_count, 2)
        # Check defaults logic - TSLA 15 should lead to pe < 15
        mock_add_ticker.assert_any_call(state, "TSLA", "pe", "<", 15.0)
        mock_add_ticker.assert_any_call(state, "MSFT", "price", ">", 300.0)
        
    @patch('scanner.yf.Ticker')
    def test_scanner_run(self, mock_ticker):
        mock_info = {"currentPrice": 150.0, "trailingPE": 20.0}
        mock_ticker.return_value.info = mock_info
        
        state = {
            "watchlist": {
                "AAPL": {
                    "name": "Apple",
                    "alerts": [
                        {"metric": "pe", "operator": "<", "target": 25.0, "is_triggered": False},
                        {"metric": "price", "operator": ">", "target": 200.0, "is_triggered": False}
                    ]
                }
            },
            "last_update_id": 0
        }
        
        mock_send = MagicMock()
        new_state = run_fundamental_scan(state, mock_send)
        
        # PE < 25 should trigger (20 < 25), price > 200 should NOT trigger (150 is not > 200)
        self.assertEqual(mock_send.call_count, 1)
        self.assertTrue(new_state["watchlist"]["AAPL"]["alerts"][0]["is_triggered"])
        self.assertFalse(new_state["watchlist"]["AAPL"]["alerts"][1]["is_triggered"])

if __name__ == '__main__':
    unittest.main()
