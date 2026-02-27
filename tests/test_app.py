"""
AnimeJapanese Test Suite
Run: python -m pytest tests/ -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module
from app import app, build_nihongocards, parse_subtitle_file


# ─────────────────────────────────────────────
# 1. Unit: VTT Subtitle Parser
# ─────────────────────────────────────────────

class TestParseSubtitleFile(unittest.TestCase):
    def _write_vtt(self, content):
        f = tempfile.NamedTemporaryFile(suffix=".vtt", mode="w", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_basic_vtt(self):
        path = self._write_vtt("""WEBVTT

00:00:01.000 --> 00:00:03.000
おはようございます。

00:00:04.000 --> 00:00:06.000
今日もよろしくお願いします。
""")
        text = parse_subtitle_file(path)
        self.assertIn("おはようございます", text)
        self.assertIn("今日もよろしくお願いします", text)
        os.unlink(path)

    def test_dedup_repeated_lines(self):
        path = self._write_vtt("""WEBVTT

00:00:01.000 --> 00:00:02.000
繰り返し

00:00:02.000 --> 00:00:03.000
繰り返し

00:00:03.000 --> 00:00:04.000
別の行
""")
        text = parse_subtitle_file(path)
        self.assertEqual(text.count("繰り返し"), 1)
        os.unlink(path)

    def test_strips_html_tags(self):
        path = self._write_vtt("""WEBVTT

00:00:01.000 --> 00:00:02.000
<c>これはテストです</c>
""")
        text = parse_subtitle_file(path)
        self.assertIn("これはテストです", text)
        self.assertNotIn("<c>", text)
        os.unlink(path)

    def test_empty_vtt(self):
        path = self._write_vtt("WEBVTT\n\n")
        text = parse_subtitle_file(path)
        self.assertEqual(text.strip(), "")
        os.unlink(path)


# ─────────────────────────────────────────────
# 2. Unit: .nihongocards Builder
# ─────────────────────────────────────────────

class TestBuildNihongocards(unittest.TestCase):
    def setUp(self):
        self.vocab = [
            {"japanese": "呼吸", "reading": "こきゅう", "chinese": "呼吸", "notes": "名詞"},
            {"japanese": "鬼", "reading": "おに", "chinese": "鬼", "notes": "名詞"},
        ]
        self.grammar = [
            {"japanese": "お前が死ぬというのなら俺も死ぬ。", "reading": "",
             "chinese": "如果你要死我也陪你。", "notes": "文法：〜というのなら"},
        ]

    def _make_data(self):
        return {"vocabulary": self.vocab, "grammar": self.grammar}

    def test_structure(self):
        result = build_nihongocards("鬼滅の刃", self._make_data())
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["type"], "group")
        self.assertIn("鬼滅の刃", result["title"])
        self.assertEqual(len(result["tables"]), 2)

    def test_vocabulary_table(self):
        result = build_nihongocards("テスト", self._make_data())
        vocab_table = next(t for t in result["tables"] if t["bookType"] == "vocabulary")
        self.assertEqual(len(vocab_table["items"]), 2)
        self.assertEqual(vocab_table["items"][0]["japanese"], "呼吸")
        self.assertEqual(vocab_table["items"][0]["reading"], "こきゅう")

    def test_grammar_table(self):
        result = build_nihongocards("テスト", self._make_data())
        grammar_table = next(t for t in result["tables"] if t["bookType"] == "grammar")
        self.assertEqual(len(grammar_table["items"]), 1)
        self.assertIn("というのなら", grammar_table["items"][0]["notes"])

    def test_json_serializable(self):
        result = build_nihongocards("テスト", self._make_data())
        json.dumps(result)  # Should not raise


# ─────────────────────────────────────────────
# 3. Integration: Flask API Endpoints
# ─────────────────────────────────────────────

class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_returns_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AnimeJapanese", resp.data)

    def test_analyze_missing_url(self):
        resp = self.client.post("/analyze",
            json={"api_key": "sk-ant-test"},
            content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    def test_analyze_invalid_url(self):
        resp = self.client.post("/analyze",
            json={"url": "not-a-url", "api_key": "sk-ant-test"},
            content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_analyze_missing_api_key(self):
        resp = self.client.post("/analyze",
            json={"url": "https://www.youtube.com/watch?v=test"},
            content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("API Key", data["error"])

    @patch("app.download_subtitles", return_value=(None, None))
    def test_analyze_no_subtitles(self, mock_dl):
        resp = self.client.post("/analyze",
            json={"url": "https://www.youtube.com/watch?v=test123", "api_key": "sk-ant-test"},
            content_type="application/json")
        self.assertEqual(resp.status_code, 422)
        data = resp.get_json()
        self.assertIn("字幕", data["error"])

    @patch("app.call_claude")
    @patch("app.download_subtitles")
    def test_analyze_success(self, mock_dl, mock_claude):
        mock_dl.return_value = ("おはようございます。今日もよろしく。", "テストアニメ")
        mock_claude.return_value = {
            "vocabulary": [
                {"japanese": "挨拶", "reading": "あいさつ", "chinese": "打招呼", "notes": "名詞"}
            ],
            "grammar": [
                {"japanese": "よろしくお願いします。", "reading": "",
                 "chinese": "請多關照。", "notes": "文法：よろしく〜"}
            ]
        }
        resp = self.client.post("/analyze",
            json={"url": "https://www.youtube.com/watch?v=test123", "api_key": "sk-ant-test"},
            content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["title"], "テストアニメ")
        self.assertEqual(len(data["vocabulary"]), 1)
        self.assertEqual(len(data["grammar"]), 1)
        self.assertIn("nihongocards", data)
        # Verify .nihongocards structure
        nc = data["nihongocards"]
        self.assertEqual(nc["version"], 1)
        self.assertEqual(len(nc["tables"]), 2)


# ─────────────────────────────────────────────
# 4. Integration: Real YouTube Subtitle Download
#    (Skipped in CI — requires Chrome cookies + network)
# ─────────────────────────────────────────────

@unittest.skipUnless(os.getenv("RUN_LIVE_TESTS"), "Set RUN_LIVE_TESTS=1 to run")
class TestLiveSubtitleDownload(unittest.TestCase):
    TEST_URL = "https://www.youtube.com/watch?v=XgRpytuQAAM"

    def test_download_japanese_subtitles(self):
        text, title = app_module.download_subtitles(self.TEST_URL, tempfile.mkdtemp())
        self.assertIsNotNone(text, "Should get subtitle text")
        self.assertIsNotNone(title, "Should get video title")
        self.assertGreater(len(text), 100, "Subtitle text should be non-trivial")
        # Should contain Japanese characters
        import unicodedata
        has_japanese = any(
            unicodedata.name(c, "").startswith(("HIRAGANA", "KATAKANA", "CJK"))
            for c in text
        )
        self.assertTrue(has_japanese, "Should contain Japanese characters")
        print(f"\n✅ Title: {title}")
        print(f"✅ Subtitle length: {len(text)} chars")
        print(f"✅ Preview: {text[:200]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
