import importlib.util
import unittest
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path('/Users/nine1ll/주식')
SPEC = importlib.util.spec_from_file_location('web_server', ROOT / 'web_server.py')
ws = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ws)


class DecisionLogicTests(unittest.TestCase):
    def test_signal_label_thresholds(self):
        self.assertEqual(ws.signal_label(70), '상승 우세')
        self.assertEqual(ws.signal_label(35), '하락 우세')
        self.assertEqual(ws.signal_label(50), '중립')

    def test_scenario_impact_sector_sensitivity(self):
        # 자동차는 EV 성장률 영향이 더 크게 반영되어야 한다.
        auto = ws.scenario_impact_pct('자동차', fx_change_pct=0.0, ev_growth_pct=10.0)
        ai = ws.scenario_impact_pct('AI', fx_change_pct=0.0, ev_growth_pct=10.0)
        self.assertGreater(auto, ai)

    def test_sector_relative_percentile_annotation(self):
        rows = [
            {"ticker": "A", "market": "KR", "sector": "반도체", "undervalued_rank": 90.0},
            {"ticker": "B", "market": "KR", "sector": "반도체", "undervalued_rank": 70.0},
            {"ticker": "C", "market": "KR", "sector": "반도체", "undervalued_rank": 50.0},
        ]
        out = ws.annotate_sector_relative_scores(rows)
        by_ticker = {x["ticker"]: x for x in out}
        self.assertEqual(by_ticker["A"]["sector_rank"], 1)
        self.assertEqual(by_ticker["B"]["sector_rank"], 2)
        self.assertEqual(by_ticker["C"]["sector_rank"], 3)
        self.assertEqual(by_ticker["A"]["sector_percentile"], 100.0)
        self.assertEqual(by_ticker["C"]["sector_percentile"], 0.0)

    def test_build_value_playbook_returns_three_reasons_and_risks(self):
        playbook = ws.build_value_playbook(
            quote={"current_price": 100},
            fundamentals={"pe_ratio": 10, "pb_ratio": 1.1, "roe": 14, "operating_margin_ttm": 9, "market_cap": 50000000000},
            relative={"sector_average": {"pe": 16, "pb": 1.8, "roe": 10}},
            risk={"total": 4.8},
            quality=70,
            tech_strength=62,
            capital_power=68,
            valuation=72,
            composite=75,
            hype=40,
        )
        self.assertEqual(len(playbook["undervalued_reasons"]), 3)
        self.assertEqual(len(playbook["value_trap_risks"]), 3)
        self.assertIn(playbook["action"]["stance"], {"매수", "관망", "비중축소"})

    def test_sector_heat_signal_detects_fragile_thematic_rally(self):
        out = ws.compute_sector_heat_signal(
            quote={"percent_change": 9.2},
            news={"ok": True, "count": 12},
            hype=82,
            quality=44,
            capital_power=42,
            valuation=38,
        )
        self.assertGreaterEqual(out["heat_score"], 65)
        self.assertLess(out["resilience_score"], 52)
        self.assertEqual(out["label"], "테마동반급등(체력취약)")

    def test_sector_heat_signal_detects_resilient_leader(self):
        out = ws.compute_sector_heat_signal(
            quote={"percent_change": 8.1},
            news={"ok": True, "count": 8},
            hype=55,
            quality=78,
            capital_power=74,
            valuation=69,
        )
        self.assertGreaterEqual(out["heat_score"], 58)
        self.assertGreaterEqual(out["resilience_score"], 62)
        self.assertEqual(out["label"], "섹터상승+체력동반(추세지속후보)")

    def test_classify_backtest_sector_signal_labels(self):
        self.assertEqual(
            ws.classify_backtest_sector_signal(70, 40, 5.0, 12.0),
            "테마동반급등(체력취약)",
        )
        self.assertEqual(
            ws.classify_backtest_sector_signal(62, 70, 2.0, 6.0),
            "섹터상승+체력동반(추세지속후보)",
        )
        self.assertEqual(
            ws.classify_backtest_sector_signal(45, 70, 1.0, 4.0),
            "저평가 체력 우위",
        )

    def test_canonical_sector_detects_securities_from_name(self):
        sec = ws.canonical_sector("", name="SK증권", industry="")
        self.assertEqual(sec, "증권")

    def test_canonical_sector_detects_it_service(self):
        sec = ws.canonical_sector("", name="삼성에스디에스", industry="IT Services")
        self.assertEqual(sec, "IT서비스")

    def test_compute_backtest_signal_row_outputs_forward_return(self):
        base = datetime(2025, 1, 1)
        points = []
        for i in range(40):
            close = 100 + (i * 0.8)
            points.append(
                {
                    "date": (base + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "close": close,
                    "volume": 1_000_000 + (i * 1000),
                }
            )
        rec = ws.compute_backtest_signal_row(points, idx=30, hold_days=5)
        self.assertIsNotNone(rec)
        self.assertIn("forward_return_pct", rec)
        self.assertIn("heat_score", rec)
        self.assertIn("resilience_score", rec)
        self.assertIn("label", rec)

    def test_lookup_company_handles_posco_typo_query(self):
        out = ws.lookup_company("POSCE홀딩스", market="KR", limit=10)
        self.assertTrue(out.get("ok"))
        items = out.get("items", [])
        self.assertTrue(any(str(x.get("ticker")) == "005490" for x in items))


if __name__ == '__main__':
    unittest.main()
