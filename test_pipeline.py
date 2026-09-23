import unittest
from unittest.mock import patch

import main
from notifier import _render_md


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.repo = {"full_name": "acme/test", "language": "Go", "stars": "100",
                     "today_stars": "1,234 stars today", "summary": "中文分析",
                     "url": "https://github.com/acme/test"}
        self.config = {"feishu": {"app_id": "test", "app_secret": "test", "chat_id": "test"}}

    def test_render_title_once_and_localize_growth(self):
        for mode, period in [("daily", "今日"), ("weekly", "本周")]:
            title, body = _render_md([self.repo], mode)
            self.assertNotIn(title, body)
            self.assertNotIn("stars today", body)
            self.assertIn(f"{period} +1,234", body)

    def run_main(self, responses, repos=None):
        with patch("sys.argv", ["main.py"]), \
             patch("main.load_config", return_value=self.config), \
             patch("main.fetch_trending", return_value=[self.repo] if repos is None else repos), \
             patch("main.summarize", side_effect=responses) as summarize, \
             patch("main.time.sleep") as sleep, \
             patch("main.send_feishu") as send:
            error = None
            try:
                main.main()
            except SystemExit as exc:
                error = exc
            return error, summarize, sleep, send

    def test_failed_summaries_never_send(self):
        error, summarize, sleep, send = self.run_main(RuntimeError("EOF"))
        self.assertIsNotNone(error)
        self.assertEqual(summarize.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        send.assert_not_called()

    def test_transient_failure_recovers_and_sends_once(self):
        error, summarize, sleep, send = self.run_main([RuntimeError("EOF"), [self.repo]])
        self.assertIsNone(error)
        self.assertEqual(summarize.call_count, 2)
        send.assert_called_once()

    def test_empty_trending_never_calls_model_or_sends(self):
        error, summarize, sleep, send = self.run_main([], repos=[])
        self.assertIsNotNone(error)
        summarize.assert_not_called()
        send.assert_not_called()
