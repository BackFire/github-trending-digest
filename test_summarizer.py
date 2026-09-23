import unittest
from unittest.mock import Mock, patch

from summarizer import SUMMARY_UNAVAILABLE, _call_openai_compat, _parse_summaries, summarize


class SummaryParserTest(unittest.TestCase):
    @patch("summarizer.OpenAI")
    def test_uses_local_gpt_model_proxy_without_client_credentials(self, openai_cls):
        openai_cls.return_value.responses.create.return_value = Mock(output_text="ok")

        result = _call_openai_compat(
            "prompt",
            api_key="",
            model="gpt-6-sol",
            cfg={"provider": "gpt-model-proxy", "base_url": "http://127.0.0.1:8787/v1"},
        )

        self.assertEqual(result, "ok")
        openai_cls.assert_called_once_with(
            api_key="gpt-model-proxy",
            base_url="http://127.0.0.1:8787/v1",
            max_retries=2,
            timeout=180,
        )
        openai_cls.return_value.responses.create.assert_called_once_with(
            model="gpt-6-sol",
            max_output_tokens=8192,
            input="prompt",
        )

    def test_preserves_multiline_summary(self):
        raw = (
            "项目名：acme/one\n"
            "简介：这是第一句中文简介。\n"
            "这是第二句中文简介。\n\n"
            "---\n\n"
            "项目名：acme/two\n"
            "简介：这是另一个项目的中文简介。"
        )

        self.assertEqual(
            _parse_summaries(raw),
            {
                "acme/one": "这是第一句中文简介。\n这是第二句中文简介。",
                "acme/two": "这是另一个项目的中文简介。",
            },
        )

    def test_rejects_missing_or_english_summary(self):
        repos = [
            {
                "full_name": "acme/one",
                "url": "https://github.com/acme/one",
                "description": "English source description",
                "language": "Python",
                "topics": [],
                "readme_excerpt": "README",
            },
            {
                "full_name": "acme/two",
                "url": "https://github.com/acme/two",
                "description": "Another English source description",
                "language": "Python",
                "topics": [],
                "readme_excerpt": "README",
            },
        ]
        raw = "项目名：acme/one\n简介：An English-only summary."

        with patch("summarizer._call_openai_compat", return_value=raw):
            with self.assertRaisesRegex(ValueError, "acme/one, acme/two"):
                summarize(repos, model="gpt-6-sol")


if __name__ == "__main__":
    unittest.main()
