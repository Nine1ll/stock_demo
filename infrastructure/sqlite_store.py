"""SQLite persistence adapter for stock app data access."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class StockAppStore:
    """Infrastructure adapter encapsulating SQLite read/write operations."""

    def __init__(
        self,
        db_path: Path,
        now_provider: Callable[[], str],
        company_name_resolver: Callable[[str, str], str],
        state_key_builder: Callable[[str, str], str],
    ) -> None:
        self._db_path = Path(db_path)
        self._now = now_provider
        self._resolve_company_name = company_name_resolver
        self._state_key_for_market = state_key_builder

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                  user_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  notes TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (user_id, ticker, market)
                );

                CREATE TABLE IF NOT EXISTS alert_rules (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  rule_type TEXT NOT NULL,
                  threshold REAL NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  UNIQUE(user_id, ticker, market, rule_type)
                );

                CREATE TABLE IF NOT EXISTS user_channels (
                  user_id TEXT PRIMARY KEY,
                  email TEXT NOT NULL DEFAULT '',
                  webhook_url TEXT NOT NULL DEFAULT '',
                  onesignal_external_id TEXT NOT NULL DEFAULT '',
                  push_enabled INTEGER NOT NULL DEFAULT 0,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notifications (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  kind TEXT NOT NULL,
                  message TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  delivered_email INTEGER NOT NULL DEFAULT 0,
                  delivered_webhook INTEGER NOT NULL DEFAULT 0,
                  delivered_push INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS alert_state (
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  state_key TEXT NOT NULL,
                  state_value TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY (user_id, ticker, state_key)
                );
                """
            )
            watch_cols = {r["name"] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
            if "market" not in watch_cols:
                conn.execute("ALTER TABLE watchlist ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
            rule_cols = {r["name"] for r in conn.execute("PRAGMA table_info(alert_rules)").fetchall()}
            if "market" not in rule_cols:
                conn.execute("ALTER TABLE alert_rules ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
            channel_cols = {r["name"] for r in conn.execute("PRAGMA table_info(user_channels)").fetchall()}
            if "onesignal_external_id" not in channel_cols:
                conn.execute("ALTER TABLE user_channels ADD COLUMN onesignal_external_id TEXT NOT NULL DEFAULT ''")
            if "push_enabled" not in channel_cols:
                conn.execute("ALTER TABLE user_channels ADD COLUMN push_enabled INTEGER NOT NULL DEFAULT 0")
            notif_cols = {r["name"] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()}
            if "market" not in notif_cols:
                conn.execute("ALTER TABLE notifications ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
            if "delivered_push" not in notif_cols:
                conn.execute("ALTER TABLE notifications ADD COLUMN delivered_push INTEGER NOT NULL DEFAULT 0")
            state_cols = {r["name"] for r in conn.execute("PRAGMA table_info(alert_state)").fetchall()}
            if "market" not in state_cols:
                conn.execute("ALTER TABLE alert_state ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")

            watch_pk = [
                r["name"]
                for r in sorted(
                    conn.execute("PRAGMA table_info(watchlist)").fetchall(),
                    key=lambda x: int(x["pk"] or 0),
                )
                if int(r["pk"] or 0) > 0
            ]
            if watch_pk != ["user_id", "ticker", "market"]:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS watchlist_v2 (
                      user_id TEXT NOT NULL,
                      ticker TEXT NOT NULL,
                      market TEXT NOT NULL DEFAULT 'US',
                      notes TEXT NOT NULL DEFAULT '',
                      created_at TEXT NOT NULL,
                      PRIMARY KEY (user_id, ticker, market)
                    );
                    INSERT OR IGNORE INTO watchlist_v2(user_id, ticker, market, notes, created_at)
                    SELECT user_id, ticker, COALESCE(NULLIF(market, ''), 'US'), notes, created_at
                    FROM watchlist;
                    DROP TABLE watchlist;
                    ALTER TABLE watchlist_v2 RENAME TO watchlist;
                    """
                )

            unique_ok = False
            for idx in conn.execute("PRAGMA index_list(alert_rules)").fetchall():
                if int(idx["unique"] or 0) != 1:
                    continue
                cols = [c["name"] for c in conn.execute(f"PRAGMA index_info('{idx['name']}')").fetchall()]
                if cols == ["user_id", "ticker", "market", "rule_type"]:
                    unique_ok = True
                    break
            if not unique_ok:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS alert_rules_v2 (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      ticker TEXT NOT NULL,
                      market TEXT NOT NULL DEFAULT 'US',
                      rule_type TEXT NOT NULL,
                      threshold REAL NOT NULL,
                      enabled INTEGER NOT NULL DEFAULT 1,
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL,
                      UNIQUE(user_id, ticker, market, rule_type)
                    );
                    INSERT OR IGNORE INTO alert_rules_v2(id, user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at)
                    SELECT id, user_id, ticker, COALESCE(NULLIF(market, ''), 'US'), rule_type, threshold, enabled, created_at, updated_at
                    FROM alert_rules;
                    DROP TABLE alert_rules;
                    ALTER TABLE alert_rules_v2 RENAME TO alert_rules;
                    """
                )

    def ensure_user(self, user_id: str) -> None:
        now = self._now()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users(user_id, created_at) VALUES (?, ?)",
                (user_id, now),
            )

    def list_watchlist(self, user_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT user_id, ticker, market, notes, created_at FROM watchlist WHERE user_id = ? ORDER BY market, ticker",
                (user_id,),
            ).fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                rec = dict(row)
                rec["company_name"] = self._resolve_company_name(str(rec.get("ticker") or ""), str(rec.get("market") or "US"))
                out.append(rec)
            return out

    def upsert_default_rules(
        self,
        user_id: str,
        ticker: str,
        market: str,
        price_change: float,
        hype_jump: float,
        filing_enabled: bool,
    ) -> None:
        now = self._now()
        rules = [
            ("price_change_pct", float(price_change), 1),
            ("hype_score_jump", float(hype_jump), 1),
            ("new_filing", 1.0, 1 if filing_enabled else 0),
        ]
        with self.connect() as conn:
            for rule_type, threshold, enabled in rules:
                conn.execute(
                    """
                    INSERT INTO alert_rules(user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, ticker, market, rule_type)
                    DO UPDATE SET threshold = excluded.threshold, enabled = excluded.enabled, updated_at = excluded.updated_at
                    """,
                    (user_id, ticker, market, rule_type, threshold, enabled, now, now),
                )

    def add_watch_item(
        self,
        user_id: str,
        ticker: str,
        market: str,
        notes: str = "",
        default_price_change: float = 5.0,
        default_hype_jump: float = 15.0,
        default_filing_enabled: bool = True,
    ) -> None:
        self.ensure_user(user_id)
        now = self._now()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist(user_id, ticker, market, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, ticker, market, notes, now),
            )
            conn.execute(
                "UPDATE watchlist SET notes = ? WHERE user_id = ? AND ticker = ? AND market = ?",
                (notes, user_id, ticker, market),
            )
        self.upsert_default_rules(
            user_id=user_id,
            ticker=ticker,
            market=market,
            price_change=default_price_change,
            hype_jump=default_hype_jump,
            filing_enabled=default_filing_enabled,
        )

    def delete_watch_item(self, user_id: str, ticker: str, market: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ? AND market = ?", (user_id, ticker, market))

    def list_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at
                FROM alert_rules
                WHERE user_id = ?
                ORDER BY market, ticker, rule_type
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_channels(self, user_id: str) -> Dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT user_id, email, webhook_url, onesignal_external_id, push_enabled, updated_at FROM user_channels WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return {"user_id": user_id, "email": "", "webhook_url": "", "onesignal_external_id": "", "push_enabled": 0}
            return dict(row)

    def set_channels(self, user_id: str, email: str, webhook_url: str, onesignal_external_id: str = "", push_enabled: bool = False) -> None:
        self.ensure_user(user_id)
        now = self._now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_channels(user_id, email, webhook_url, onesignal_external_id, push_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                  email = excluded.email,
                  webhook_url = excluded.webhook_url,
                  onesignal_external_id = excluded.onesignal_external_id,
                  push_enabled = excluded.push_enabled,
                  updated_at = excluded.updated_at
                """,
                (user_id, email.strip(), webhook_url.strip(), onesignal_external_id.strip(), 1 if push_enabled else 0, now),
            )

    def list_notifications(self, user_id: str, limit: int = 40) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, ticker, market, kind, message, payload_json, created_at, delivered_email, delivered_webhook, delivered_push
                FROM notifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            out = []
            for r in rows:
                row = dict(r)
                try:
                    row["payload"] = json.loads(row.pop("payload_json"))
                except Exception:
                    row["payload"] = {}
                out.append(row)
            return out

    def get_state(self, user_id: str, ticker: str, market: str, key: str) -> Optional[str]:
        mkey = self._state_key_for_market(market, key)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT state_value FROM alert_state WHERE user_id = ? AND ticker = ? AND state_key = ?",
                (user_id, ticker, mkey),
            ).fetchone()
            return row["state_value"] if row else None

    def set_state(self, user_id: str, ticker: str, market: str, key: str, value: str) -> None:
        now = self._now()
        mkey = self._state_key_for_market(market, key)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_state(user_id, ticker, market, state_key, state_value, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, ticker, state_key)
                DO UPDATE SET state_value = excluded.state_value, updated_at = excluded.updated_at
                """,
                (user_id, ticker, market, mkey, value, now),
            )

    def save_notification_delivery(
        self,
        user_id: str,
        ticker: str,
        market: str,
        kind: str,
        message: str,
        payload: Dict[str, Any],
        delivered_email: bool,
        delivered_webhook: bool,
        delivered_push: bool,
    ) -> None:
        now = self._now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO notifications(user_id, ticker, market, kind, message, payload_json, created_at, delivered_email, delivered_webhook, delivered_push)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    ticker,
                    market,
                    kind,
                    message,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    1 if delivered_email else 0,
                    1 if delivered_webhook else 0,
                    1 if delivered_push else 0,
                ),
            )

