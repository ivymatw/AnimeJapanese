# DESIGN.md — AnimeJapanese Design Documentation

## Design Philosophy

**Simple. Dark. Functional.**

- Zero JavaScript frameworks — vanilla JS keeps load time instant
- Dark theme reduces eye strain during late-night study sessions
- Mobile-friendly — most users might use it on iPad alongside their anime
- Progressive disclosure — settings hidden by default, results only appear when ready
- Accessibility: large tap targets, clear status feedback at every step

---

## UI Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              AnimeJapanese 🎌                           │
│    從動漫學日文 — 自動從 YouTube 動漫字幕提取 N2+ 學習素材    │
│                                                         │
│  ┌ ⚙️ 設定 (Anthropic API Key) ──────────────────────┐  │
│  │  [sk-ant-...                    ] [儲存]          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────┐ ┌──────────────┐  │
│  │ https://www.youtube.com/...     │ │  分析字幕    │  │
│  └─────────────────────────────────┘ └──────────────┘  │
│                                                         │
│  ┌── Status ──────────────────────────────────────────┐ │
│  │  ⟳  下載字幕中...                                  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  🎬 Video Title                [⬇️ 下載 .nihongocards] │
│                                                         │
│  ┌── 📚 單字 (10個) ──────────────────────────────────┐ │
│  │  日文     │ 讀音      │ 中文     │ 備注            │ │
│  │  断念     │ だんねん  │ 放棄     │ 名詞/動詞       │ │
│  │  ...      │ ...       │ ...      │ ...            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌── 📝 文法 (5句) ───────────────────────────────────┐ │
│  │  1. 彼女にもかかわらず前に進み続けた。               │ │
│  │     📖 儘管如此，她仍繼續向前。                     │ │
│  │     💡 文法重點：〜にもかかわらず（儘管…）           │ │
│  │  ...                                               │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Color Scheme

| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#0f0f13` | Page background |
| `--surface` | `#1a1a24` | Cards, inputs |
| `--surface2` | `#22222f` | Table headers, secondary bg |
| `--border` | `#2e2e42` | All borders |
| `--accent` | `#7c6af7` | Primary button, focus rings |
| `--accent-hover` | `#9585ff` | Hover state, reading text |
| `--text` | `#e8e8f0` | Primary text |
| `--text-muted` | `#888899` | Secondary text, labels |
| `--success` | `#4ade80` | Download button gradient start |
| `--error` | `#f87171` | Error messages |

**Title gradient:** `135deg, #7c6af7 → #a855f7 → #ec4899`

---

## Component Breakdown

### 1. Header
- Large gradient text title
- Muted subtitle explaining the app

### 2. Settings Panel (`<details>`)
- Collapsed by default (clean first impression)
- Password input for API key
- localStorage persistence
- Hint text about env var alternative

### 3. URL Input Row
- Full-width URL input (flex: 1)
- Enter key triggers analysis
- "分析字幕" button disables during processing

### 4. Status / Error Sections
- Status: animated spinner + rotating status messages
- Error: red background box with error text
- Mutually exclusive display

### 5. Results Section
- Header: video title + download button
- Vocabulary Card: responsive table with 4 columns
- Grammar Card: card list with JP sentence, CN translation, grammar note badge

### 6. Download
- Client-side JS blob download (no server round-trip)
- Safe filename derived from video title
- `.nihongocards` extension for iOS app association

---

## Responsive Behavior

- **Desktop (>600px):** URL input + button in one row; full table visible
- **Mobile (≤600px):** URL input + button stack vertically; table scrolls horizontally; header shrinks

---

## State Machine

```
idle
  → [user clicks 分析字幕]
loading
  → [success] → results
  → [error] → error (→ idle on next attempt)
```
