# SPEC.md — AnimeJapanese Technical Specification

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Client)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  index.html + style.css + script.js                  │   │
│  │  - URL input → POST /analyze                         │   │
│  │  - Renders vocabulary table + grammar list           │   │
│  │  - Triggers .nihongocards browser download           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP POST /analyze (JSON)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend (app.py)                    │
│                                                             │
│  1. Validate URL + API key                                  │
│  2. yt-dlp → download .vtt subtitle                        │
│  3. Parse VTT/SRT → plain text                             │
│  4. Anthropic Claude API → JSON (vocab + grammar)          │
│  5. Build .nihongocards structure                          │
│  6. Return JSON to client                                   │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────┐        ┌────────────────────┐
│  YouTube via    │        │  Anthropic Claude   │
│  yt-dlp CLI    │        │  claude-opus-4-5    │
└─────────────────┘        └────────────────────┘
```

---

## API Endpoints

### `GET /`

Returns the HTML UI.

---

### `POST /analyze`

**Request Body (JSON):**

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "api_key": "sk-ant-..." 
}
```

- `url` — YouTube video URL (required)
- `api_key` — Anthropic API key (optional if env var set)

**Success Response (200):**

```json
{
  "title": "Video Title",
  "vocabulary": [
    {
      "japanese": "断念",
      "reading": "だんねん",
      "chinese": "放棄、斷念",
      "notes": "名詞/動詞（する）"
    }
  ],
  "grammar": [
    {
      "japanese": "彼女にもかかわらず前に進み続けた。",
      "reading": "",
      "chinese": "儘管如此，她仍繼續向前。",
      "notes": "文法重點：〜にもかかわらず（儘管…）"
    }
  ],
  "nihongocards": { ... }
}
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing URL or invalid format |
| 401 | Invalid Anthropic API key |
| 422 | No Japanese subtitles found |
| 429 | API rate limit exceeded |
| 500 | Claude response parse error or other internal error |

---

## Data Flow

```
User URL
  → yt-dlp try official sub (--write-sub --sub-lang ja)
      → found? parse VTT → text
      → not found? try auto-sub (--write-auto-sub --sub-lang ja)
          → found? parse VTT/SRT → text
          → not found? → 422 error
  → Truncate text to 8000 chars
  → Claude API (system prompt + subtitle text)
  → Parse JSON response
  → Build nihongocards structure
  → Return to client
```

---

## .nihongocards Format

The `.nihongocards` file is a JSON file importable into the NihongoCards iOS app.

```json
{
  "version": 1,
  "type": "group",
  "title": "AnimeJapanese - [video title]",
  "exportedAt": "2026-02-27T00:00:00Z",
  "tables": [
    {
      "title": "單字 - [video title]",
      "bookType": "vocabulary",
      "items": [
        {
          "japanese": "日文單字",
          "reading": "よみかた",
          "chinese": "繁體中文翻譯",
          "notes": "詞性或使用說明"
        }
      ]
    },
    {
      "title": "文法 - [video title]",
      "bookType": "grammar",
      "items": [
        {
          "japanese": "動漫中的例句",
          "reading": "",
          "chinese": "繁體中文翻譯",
          "notes": "文法重點說明"
        }
      ]
    }
  ]
}
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| No Japanese subtitles | HTTP 422 + clear Chinese error message |
| Invalid YouTube URL | HTTP 400 + message |
| Missing API key | HTTP 400 + message |
| Wrong API key | HTTP 401 + message |
| Claude rate limit | HTTP 429 + message |
| Claude returns bad JSON | HTTP 500 + message |
| yt-dlp timeout | Subprocess timeout at 60s |
| Subtitle too long | Truncate to 8000 chars before Claude call |

---

## Configuration

| Setting | Method |
|---|---|
| Anthropic API Key | Env var `ANTHROPIC_API_KEY` or request body |
| Port | Env var `PORT` (default: 5001) |
| Claude model | `claude-opus-4-5` (hardcoded, change in app.py) |
| Max subtitle length | 8000 chars (configurable in app.py) |

---

## 測試

### 執行方式

```bash
# 安裝 pytest
pip3 install pytest

# 跑所有單元/整合測試（不需要 API Key 或網路）
python3 -m pytest tests/ -v

# 跑真實 YouTube 下載測試（需要 Chrome 登入 + 網路）
RUN_LIVE_TESTS=1 python3 -m pytest tests/ -v
```

### 測試涵蓋範圍

| 測試類 | 項目 | 說明 |
|---|---|---|
| `TestParseSubtitleFile` | 4 tests | VTT 解析、去重、HTML 清除、空檔案 |
| `TestBuildNihongocards` | 4 tests | JSON 結構、單字表、文法表、序列化 |
| `TestFlaskEndpoints` | 5 tests | URL/Key 驗證、字幕缺失、成功回應（mock） |
| `TestLiveSubtitleDownload` | 1 test (skip) | 真實 YouTube 下載（`RUN_LIVE_TESTS=1` 啟用） |

**目前狀態：14 passed, 1 skipped**

### 測試策略

- **單元測試**：mock 掉 yt-dlp 和 Claude API，純邏輯驗證
- **Live test**：用環境變數 `RUN_LIVE_TESTS=1` 開啟，驗證真實字幕下載流程
- **CI 注意**：`TestLiveSubtitleDownload` 需要 Chrome cookies，不適合在 CI 環境跑
