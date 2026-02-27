# AnimeJapanese 🎌

> 從動漫學日文 — 自動從 YouTube 動漫字幕提取 N2+ 學習素材

**Learn Japanese from anime automatically.** Paste a YouTube URL, get 10 N2+ vocabulary words and 5 grammar patterns, ready to import into the NihongoCards iOS app.

---

## Features

- 🎬 **YouTube 字幕擷取** — 自動下載官方或自動生成的日文字幕
- 🤖 **AI 智慧篩選** — Claude 從字幕中選出 N2+ 程度單字與文法句型
- 📱 **NihongoCards 匯出** — 產生可直接匯入 iOS App 的 `.nihongocards` 檔案
- 🌙 **Dark UI** — 簡潔的深色介面，支援手機瀏覽器
- 🔑 **彈性 API Key** — 可透過環境變數或 UI 設定輸入

---

## Installation

### Prerequisites

- Python 3.10+
- Anthropic API Key (get one at [console.anthropic.com](https://console.anthropic.com))

### Steps

```bash
# Clone the repo
git clone https://github.com/ivymatw/AnimeJapanese.git
cd AnimeJapanese

# Install dependencies
pip install -r requirements.txt

# Set your API key (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the app
python app.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

---

## Usage

1. Open the app in your browser
2. (Optional) Enter your Anthropic API Key in Settings if not set via env var
3. Paste a YouTube URL of a Japanese anime video with subtitles
4. Click **分析字幕**
5. Wait ~15–30 seconds for subtitle download + AI analysis
6. Preview vocabulary and grammar results
7. Click **下載 .nihongocards 檔案** to export
8. Import the file into [NihongoCards](https://github.com/ivymatw/NihongoCard) iOS app

---

## Screenshot

> *(Screenshot coming soon)*

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python + Flask |
| Subtitle extraction | yt-dlp |
| AI analysis | Anthropic Claude API |
| Frontend | Plain HTML + CSS + JS |

---

## Related Projects

- 📱 [NihongoCards iOS App](https://github.com/ivymatw/NihongoCard) — the flashcard app that imports `.nihongocards` files

---

## License

MIT
