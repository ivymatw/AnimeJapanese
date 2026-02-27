/* AnimeJapanese - Frontend Script */

const LS_KEY = "animejapanese_api_key";
let currentCards = null;

// ── Init ──────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem(LS_KEY);
  if (saved) document.getElementById("api-key").value = saved;
});

function saveKey() {
  const key = document.getElementById("api-key").value.trim();
  if (key) {
    localStorage.setItem(LS_KEY, key);
    showStatus("✅ API Key 已儲存");
    setTimeout(clearStatus, 2000);
  }
}

// ── Analyze ───────────────────────────────────────────
async function analyze() {
  const url = document.getElementById("youtube-url").value.trim();
  const apiKey = document.getElementById("api-key").value.trim() || localStorage.getItem(LS_KEY) || "";

  if (!url) {
    showError("請貼上 YouTube 影片網址");
    return;
  }

  hideResults();
  hideError();
  setAnalyzeBtn(true);

  // Step 1
  showStatus("⬇️ 下載字幕中...");
  await sleep(300); // let UI paint

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, api_key: apiKey }),
    });

    if (res.status === 202 || res.ok) {
      // Progress hint while waiting
      const progressTimer = cycleStatus([
        "⬇️ 下載字幕中...",
        "⬇️ 下載字幕中（可能需要 10-30 秒）...",
        "🤖 分析中，請稍候...",
        "🤖 Claude 正在選取 N2+ 單字與文法...",
      ]);

      const data = await res.json();
      clearInterval(progressTimer);

      if (!res.ok) {
        showError(data.error || "發生未知錯誤");
        return;
      }

      currentCards = data.nihongocards;
      showStatus("✅ 完成！");
      setTimeout(clearStatus, 1500);
      renderResults(data);

    } else {
      const data = await res.json().catch(() => ({}));
      showError(data.error || `HTTP ${res.status} 錯誤`);
    }
  } catch (err) {
    showError("連線錯誤：" + err.message);
  } finally {
    setAnalyzeBtn(false);
  }
}

// ── Render ────────────────────────────────────────────
function renderResults(data) {
  document.getElementById("video-title-display").textContent = `🎬 ${data.title}`;

  // Vocabulary table
  const tbody = document.getElementById("vocab-body");
  tbody.innerHTML = "";
  (data.vocabulary || []).forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${esc(item.japanese)}</td>
      <td>${esc(item.reading)}</td>
      <td>${esc(item.chinese)}</td>
      <td>${esc(item.notes)}</td>
    `;
    tbody.appendChild(tr);
  });
  document.getElementById("vocab-count").textContent = `${(data.vocabulary || []).length} 個`;

  // Grammar list
  const grammarDiv = document.getElementById("grammar-list");
  grammarDiv.innerHTML = "";
  (data.grammar || []).forEach((item, i) => {
    const el = document.createElement("div");
    el.className = "grammar-item";
    el.innerHTML = `
      <div class="grammar-jp">${i + 1}. ${esc(item.japanese)}</div>
      <div class="grammar-cn">📖 ${esc(item.chinese)}</div>
      ${item.notes ? `<span class="grammar-note">💡 ${esc(item.notes)}</span>` : ""}
    `;
    grammarDiv.appendChild(el);
  });
  document.getElementById("grammar-count").textContent = `${(data.grammar || []).length} 句`;

  document.getElementById("results-section").classList.remove("hidden");
}

// ── Download ──────────────────────────────────────────
function downloadCards() {
  if (!currentCards) return;
  const json = JSON.stringify(currentCards, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const safeName = (currentCards.title || "AnimeJapanese")
    .replace(/[^a-zA-Z0-9\u3040-\u9fff\s-]/g, "")
    .trim()
    .replace(/\s+/g, "_")
    .slice(0, 60);
  a.download = `${safeName}.nihongocards`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── UI helpers ────────────────────────────────────────
function showStatus(msg) {
  document.getElementById("status-text").textContent = msg;
  document.getElementById("status-section").classList.remove("hidden");
}

function clearStatus() {
  document.getElementById("status-section").classList.add("hidden");
}

function showError(msg) {
  document.getElementById("error-text").textContent = msg;
  document.getElementById("error-section").classList.remove("hidden");
  document.getElementById("status-section").classList.add("hidden");
}

function hideError() {
  document.getElementById("error-section").classList.add("hidden");
}

function hideResults() {
  document.getElementById("results-section").classList.add("hidden");
}

function setAnalyzeBtn(disabled) {
  const btn = document.getElementById("analyze-btn");
  btn.disabled = disabled;
  btn.textContent = disabled ? "分析中..." : "分析字幕";
}

function cycleStatus(messages) {
  let i = 0;
  return setInterval(() => {
    i = (i + 1) % messages.length;
    showStatus(messages[i]);
  }, 3000);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
