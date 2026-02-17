import tempfile
import unittest
from pathlib import Path

from infrastructure.sqlite_store import StockAppStore


class SqliteStoreTests(unittest.TestCase):
    def _build_store(self, db_path: Path) -> StockAppStore:
        return StockAppStore(
            db_path=db_path,
            now_provider=lambda: "2026-02-17T00:00:00+00:00",
            company_name_resolver=lambda ticker, market: f"{ticker}-{market}",
            state_key_builder=lambda market, key: f"{market}:{key}",
        )

    def test_watchlist_and_default_rules_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            store = self._build_store(Path(td) / "app.db")
            store.init_db()
            store.add_watch_item(
                user_id="u1",
                ticker="AAPL",
                market="US",
                notes="core",
                default_price_change=5.0,
                default_hype_jump=15.0,
                default_filing_enabled=True,
            )

            watch = store.list_watchlist("u1")
            self.assertEqual(len(watch), 1)
            self.assertEqual(watch[0]["company_name"], "AAPL-US")

            rules = store.list_alerts("u1")
            self.assertEqual(len(rules), 3)

    def test_channels_state_and_notifications(self):
        with tempfile.TemporaryDirectory() as td:
            store = self._build_store(Path(td) / "app.db")
            store.init_db()
            store.set_channels("u2", "a@b.com", "https://example.com/hook", "ext-1", True)
            channels = store.get_channels("u2")
            self.assertEqual(channels["email"], "a@b.com")
            self.assertEqual(int(channels["push_enabled"]), 1)

            store.set_state("u2", "005930", "KR", "heat", "70")
            self.assertEqual(store.get_state("u2", "005930", "KR", "heat"), "70")

            store.save_notification_delivery(
                user_id="u2",
                ticker="005930",
                market="KR",
                kind="price_change_pct",
                message="alert",
                payload={"score": 70},
                delivered_email=True,
                delivered_webhook=False,
                delivered_push=True,
            )
            rows = store.list_notifications("u2", limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["payload"]["score"], 70)


if __name__ == "__main__":
    unittest.main()

