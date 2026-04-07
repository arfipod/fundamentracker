import unittest
from unittest.mock import Mock, patch

from src import main


class TestTelegramAlert(unittest.TestCase):
    def test_send_telegram_alert_success(self):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post = Mock(return_value=mock_response)

        ok = main.send_telegram_alert("hello", token="t", chat_id="c", post=mock_post)

        self.assertTrue(ok)
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bott/sendMessage",
            json={"chat_id": "c", "text": "hello", "parse_mode": "Markdown"},
        )

    @patch("builtins.print")
    def test_send_telegram_alert_failure(self, mock_print):
        mock_post = Mock(side_effect=RuntimeError("boom"))

        ok = main.send_telegram_alert("hello", token="t", chat_id="c", post=mock_post)

        self.assertFalse(ok)
        mock_print.assert_called_once()


class TestAlertFormatting(unittest.TestCase):
    def test_build_valuation_alert_format(self):
        msg = main.build_valuation_alert("Apple", "AAPL", 20.1234, 190)
        self.assertIn("Apple", msg)
        self.assertIn("AAPL", msg)
        self.assertIn("20.12", msg)
        self.assertIn("$190", msg)


class TestRunScan(unittest.TestCase):
    @patch("builtins.print")
    def test_run_scan_alerts_when_pe_below_threshold(self, _mock_print):
        class FakeTicker:
            def __init__(self, symbol):
                self.info = {
                    "currentPrice": 100,
                    "trailingPE": 10 if symbol == "AAPL" else 30,
                }

        alert_sender = Mock(return_value=True)
        watchlist = [
            {"ticker": "AAPL", "name": "Apple"},
            {"ticker": "TSLA", "name": "Tesla"},
        ]

        alerted = main.run_scan(watchlist=watchlist, ticker_factory=FakeTicker, alert_sender=alert_sender)

        self.assertEqual(alerted, ["AAPL"])
        alert_sender.assert_called_once()

    @patch("builtins.print")
    def test_run_scan_handles_ticker_errors(self, mock_print):
        class FailingTicker:
            def __init__(self, _symbol):
                raise ValueError("network")

        alerted = main.run_scan(
            watchlist=[{"ticker": "AAPL", "name": "Apple"}],
            ticker_factory=FailingTicker,
            alert_sender=Mock(),
        )

        self.assertEqual(alerted, [])
        self.assertTrue(any("Error processing AAPL" in args[0] for args, _ in mock_print.call_args_list))


class TestMainEntrypoint(unittest.TestCase):
    def test_main_runs_connection_test(self):
        with patch("src.main.run_connection_test") as run_test, patch("src.main.run_scan") as run_scan:
            code = main.main(["--test"])

        self.assertEqual(code, 0)
        run_test.assert_called_once_with()
        run_scan.assert_not_called()

    def test_main_runs_scan_without_args(self):
        with patch("src.main.run_connection_test") as run_test, patch("src.main.run_scan") as run_scan:
            code = main.main([])

        self.assertEqual(code, 0)
        run_scan.assert_called_once_with()
        run_test.assert_not_called()


if __name__ == "__main__":
    unittest.main()
