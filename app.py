#!/usr/bin/env python3
"""AnimeJapanese - Flask backend for extracting Japanese learning content from anime subtitles."""

from __future__ import annotations
import os
import re
import json
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template
import anthropic

app = Flask(__name__)

SYSTEM_PROMPT = """你是日文學習助手，專門從日本動漫對白中選取適合 N2 程度以上的學習素材。

請從以下動漫字幕中：
1. 選出 20 個 N2 以上程度的重要單字（避免太基礎的 N5/N4 單字）
2. 選出 10 個包含重要文法的例句（N2 以上文法，如 〜にもかかわらず、〜に際して、〜を踏まえて 等）

要求：
- 單字需提供假名讀音和繁體中文翻譯
- 例句直接從字幕原文擷取（不要改寫）
- 翻譯使用繁體中文
- 以 JSON 格式回傳，格式如下：

{
  "vocabulary": [
    {"japanese": "単語", "reading": "たんご", "chinese": "單字", "notes": "名詞/動詞/形容詞等說明"}
  ],
  "grammar": [
    {"japanese": "例句原文", "reading": "", "chinese": "繁體中文翻譯", "notes": "文法重點：〜文法型"}
  ]
}

只回傳 JSON，不要其他文字。"""


def get_api_key(request_body=None):
    """Get Anthropic API key from env or request body."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and request_body:
        key = request_body.get("api_key", "").strip()
    return key


def download_subtitles(url: str, tmpdir: str) -> tuple[str | None, str | None]:
    """
    Try to download Japanese subtitles. Returns (subtitle_text, video_title) or (None, None).
    Tries official subs first, then auto-generated.
    """
    # Use %(title)s so the filename contains the video title
    base_path = os.path.join(tmpdir, "%(title)s")

    # Use Python 3.9 yt-dlp (Homebrew 2026.x has JS runtime issues with YouTube)
    import shutil
    ytdlp_bin = "/Users/ivyma/Library/Python/3.9/bin/yt-dlp"
    if not Path(ytdlp_bin).exists():
        ytdlp_bin = shutil.which("yt-dlp") or "yt-dlp"

    # Common yt-dlp args (no --print title — it prevents subtitle file creation)
    common_args = [
        ytdlp_bin,
        "--skip-download",
        "--sub-lang", "ja",
        "--convert-subs", "vtt",
        "-o", base_path,
        "--no-warnings",
        "--cookies-from-browser", "chrome",
    ]

    def run_and_check(extra_args):
        """Run yt-dlp, return (subtitle_text, title) or (None, None)."""
        try:
            subprocess.run(common_args + extra_args + [url],
                capture_output=True, text=True, timeout=60)
            vtt_files = list(Path(tmpdir).glob("*.vtt"))
            if vtt_files:
                # Extract title from filename: "Title.ja.vtt" → "Title"
                stem = vtt_files[0].stem  # e.g. "葬送的芙莉蓮 第29話.ja"
                title = stem.rsplit(".", 1)[0] if "." in stem else stem
                return parse_subtitle_file(str(vtt_files[0])), title
        except Exception:
            pass
        return None, None

    # Try 1: official subs
    text, title = run_and_check(["--write-sub"])
    if text:
        return text, title

    # Try 2: auto-generated subs
    text, title = run_and_check(["--write-auto-sub"])
    if text:
        return text, title

    # Try 3: both together
    text, title = run_and_check(["--write-sub", "--write-auto-sub"])
    if text:
        return text, title

    return None, None


def parse_subtitle_file(filepath: str) -> str:
    """Parse VTT or SRT file and return plain text (deduplicated)."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    ext = Path(filepath).suffix.lower()
    lines = []

    if ext == ".vtt":
        # Remove WEBVTT header and cue settings
        content = re.sub(r"WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
        # Remove timestamps (00:00:00.000 --> 00:00:00.000 ...)
        content = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}[^\n]*", "", content)
        # Remove VTT tags like <c>, <00:00:00.000>
        content = re.sub(r"<[^>]+>", "", content)
        # Remove cue identifiers (numeric lines)
        content = re.sub(r"^\d+$", "", content, flags=re.MULTILINE)
    elif ext == ".srt":
        # Remove timestamps
        content = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}", "", content)
        # Remove numeric cue IDs
        content = re.sub(r"^\d+$", "", content, flags=re.MULTILINE)
        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", content)

    # Collect non-empty lines, deduplicate consecutive identical lines
    seen = set()
    for line in content.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)

    return "\n".join(lines)


def call_claude(subtitle_text: str, api_key: str) -> dict:
    """Send subtitle text to Claude and get vocabulary + grammar JSON."""
    client = anthropic.Anthropic(api_key=api_key)

    # Limit subtitle length to avoid token overflow
    max_chars = 8000
    if len(subtitle_text) > max_chars:
        subtitle_text = subtitle_text[:max_chars] + "\n...(字幕截斷)"

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"以下是動漫字幕內容：\n\n{subtitle_text}"}
        ]
    )

    text = message.content[0].text.strip()
    # Strip markdown code blocks if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def build_nihongocards(title: str, data: dict) -> dict:
    """Build .nihongocards JSON structure."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": 1,
        "type": "group",
        "title": f"AnimeJapanese - {title}",
        "exportedAt": now,
        "tables": [
            {
                "title": f"單字 - {title}",
                "bookType": "vocabulary",
                "items": data.get("vocabulary", [])
            },
            {
                "title": f"文法 - {title}",
                "bookType": "grammar",
                "items": data.get("grammar", [])
            }
        ]
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()
    api_key = get_api_key(body)

    if not url:
        return jsonify({"error": "請提供 YouTube URL"}), 400
    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "無效的 URL 格式"}), 400
    if not api_key:
        return jsonify({"error": "請設定 Anthropic API Key（環境變數 ANTHROPIC_API_KEY 或在設定中輸入）"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Download subtitles
        subtitle_text, video_title = download_subtitles(url, tmpdir)

        if not subtitle_text:
            return jsonify({"error": "找不到日文字幕。請確認該影片有日文字幕（官方或自動生成）。"}), 422

        # Step 2: Call Claude
        try:
            data = call_claude(subtitle_text, api_key)
        except anthropic.AuthenticationError:
            return jsonify({"error": "API Key 無效，請確認 Anthropic API Key 正確。"}), 401
        except anthropic.RateLimitError:
            return jsonify({"error": "API 使用超限，請稍後再試。"}), 429
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Claude 回傳格式解析失敗：{str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"AI 分析失敗：{str(e)}"}), 500

        # Step 3: Build nihongocards
        cards = build_nihongocards(video_title, data)

        return jsonify({
            "title": video_title,
            "vocabulary": data.get("vocabulary", []),
            "grammar": data.get("grammar", []),
            "nihongocards": cards
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"🎌 AnimeJapanese running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
