import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebAssetSyncTests(unittest.TestCase):
    def test_main_app_legacy_copy_is_synced(self):
        legacy = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        canonical = (ROOT / "web" / "app_main_v35.js").read_text(encoding="utf-8")
        self.assertEqual(legacy, canonical, "web/app.js must stay in sync with web/app_main_v35.js")

    def test_decision_ui_legacy_copy_is_synced(self):
        legacy = (ROOT / "web" / "decision_ui.js").read_text(encoding="utf-8")
        canonical = (ROOT / "web" / "decision_ui_v35.js").read_text(encoding="utf-8")
        self.assertEqual(legacy, canonical, "web/decision_ui.js must stay in sync with web/decision_ui_v35.js")


if __name__ == "__main__":
    unittest.main()

