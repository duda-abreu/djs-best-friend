const form = document.getElementById("search-form");
const resultsEl = document.getElementById("results");
const resultsTitle = document.getElementById("results-title");
const resultLimitEl = document.getElementById("result-limit");

let currentView = { type: "trending" };

resultLimitEl.addEventListener("change", () => {
  if (currentView.type === "search") {
    form.dispatchEvent(new Event("submit", { cancelable: true }));
  } else if (currentView.type === "trending") {
    loadTrending();
  }
});

const nowArt = document.getElementById("now-art");
const nowTitle = document.getElementById("now-title");
const nowArtist = document.getElementById("now-artist");
const nowSource = document.getElementById("now-source");
const nowBpm = document.getElementById("now-bpm");
const nowFill = document.getElementById("now-fill");
const nowStatus = document.getElementById("now-status");
const footerMsg = document.getElementById("footer-msg");
const clockEl = document.getElementById("clock");

const statCount = document.getElementById("stat-count");
const statGb = document.getElementById("stat-gb");
const statWeek = document.getElementById("stat-week");

let currentPreviewMedia = null;
let currentPreviewBtn = null;
let spotifyAuthenticated = false;

const spotifyAuthBtn = document.getElementById("spotify-auth-btn");
spotifyAuthBtn.addEventListener("click", () => {
  window.location.href = "/auth/login";
});

async function checkSpotifyAuth() {
  try {
    const res = await fetch("/auth/status");
    const data = await res.json();
    spotifyAuthenticated = !!data.authenticated;
    spotifyAuthBtn.style.display = spotifyAuthenticated ? "none" : "";
  } catch {
    spotifyAuthenticated = false;
  }
}
checkSpotifyAuth();

document.getElementById("home-link").addEventListener("click", () => {
  stopPreview();
  resetNowPanel();
  document.getElementById("query").value = "";
  loadTrending();
});

const BPM_CONCURRENCY = 3;
let bpmActive = 0;
const bpmPending = [];

function queueBpmTask(fn) {
  bpmPending.push(fn);
  drainBpmQueue();
}

function drainBpmQueue() {
  while (bpmActive < BPM_CONCURRENCY && bpmPending.length > 0) {
    const fn = bpmPending.shift();
    bpmActive++;
    Promise.resolve()
      .then(fn)
      .catch(() => {})
      .finally(() => {
        bpmActive--;
        drainBpmQueue();
      });
  }
}

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 180;

function tickClock() {
  clockEl.textContent = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
tickClock();
setInterval(tickClock, 1000 * 30);

function formatDuration(ms) {
  const totalSec = Math.round((ms || 0) / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${String(sec).padStart(2, "0")}`;
}

let lastHistory = { entries: [] };

async function loadStats() {
  try {
    const res = await fetch("/api/history");
    if (!res.ok) return;
    const data = await res.json();
    lastHistory = data;
    statCount.textContent = data.total_songs;
    statGb.textContent = data.total_gb;
    statWeek.textContent = data.recent_week.length;
  } catch {
  }
}
loadStats();

const statsBar = document.getElementById("stats-bar");

statsBar.addEventListener("click", async () => {
  currentView = { type: "history" };
  await loadStats();
  renderHistoryList();
});

function renderHistoryList() {
  resultsTitle.textContent = "músicas baixadas";
  const entries = lastHistory.entries || [];

  if (entries.length === 0) {
    resultsEl.innerHTML = "<li class='empty-hint'>nenhuma música baixada ainda.</li>";
    return;
  }

  resultsEl.innerHTML = "";
  for (const e of entries) {
    const li = document.createElement("li");
    li.className = "result-card history-row";

    const date = new Date(e.downloaded_at * 1000).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    const gb = (e.size_bytes / (1024 ** 3)).toFixed(3);

    li.innerHTML = `
      <div class="result-info">
        <div class="title">${escapeHtml(e.title || "(sem título)")}</div>
        <div class="artist">${escapeHtml(e.artist || "")}</div>
        <div class="meta">
          <span>${date}</span>
          <span>${e.source} · ${e.quality}</span>
          <span>${gb} GB</span>
          <span>${e.bpm ? `${e.bpm} bpm` : "bpm: --"}</span>
        </div>
      </div>
      <div class="result-actions">
        <button type="button" class="glossy-btn small delete-btn">excluir</button>
      </div>
    `;

    li.querySelector(".delete-btn").addEventListener("click", () => deleteHistoryEntry(e.id, li));
    resultsEl.appendChild(li);
  }
}

async function deleteHistoryEntry(entryId, li) {
  try {
    const res = await fetch(`/api/history/${entryId}`, { method: "DELETE" });
    if (!res.ok) throw new Error();
    li.remove();
    await loadStats();
    if ((lastHistory.entries || []).length === 0) {
      resultsEl.innerHTML = "<li class='empty-hint'>nenhuma música baixada ainda.</li>";
    }
  } catch {
    footerMsg.textContent = "erro ao excluir música";
  }
}

async function loadTrending() {
  currentView = { type: "trending" };
  resultsTitle.textContent = "em alta essa semana";
  resultsEl.innerHTML = "<li class='empty-hint'>carregando sugestões...</li>";
  try {
    const res = await fetch(`/api/trending?limit=${resultLimitEl.value}`);
    if (!res.ok) throw new Error((await res.json()).detail || "erro ao carregar sugestões");
    const items = await res.json();
    renderResults(items);
  } catch (err) {
    resultsEl.innerHTML = `<li class="empty-hint">não foi possível carregar sugestões: ${escapeHtml(err.message)}</li>`;
  }
}
loadTrending();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = document.getElementById("query").value.trim();
  const source = document.getElementById("source").value;
  const limit = resultLimitEl.value;
  if (!query) return;

  currentView = { type: "search" };
  resultsTitle.textContent = `Resultados para "${query}"`;
  resultsEl.innerHTML = "<li class='empty-hint'>buscando...</li>";
  footerMsg.textContent = "buscando...";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&source=${source}&limit=${limit}`);
    if (!res.ok) throw new Error((await res.json()).detail || "erro na busca");
    const items = await res.json();
    renderResults(items);
    footerMsg.textContent = `${items.length} resultado(s)`;
  } catch (err) {
    resultsEl.innerHTML = `<li class="empty-hint">erro: ${escapeHtml(err.message)}</li>`;
    footerMsg.textContent = "erro na busca";
  }
});

function renderResults(items) {
  resultsEl.innerHTML = "";
  bpmPending.length = 0;

  if (items.length === 0) {
    resultsEl.innerHTML = "<li class='empty-hint'>nenhum resultado encontrado.</li>";
    return;
  }

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "result-card";

    const qualityOptions =
      item.source === "spotify"
        ? [["320k", "mp3 320k"]]
        : [
            ["original", "original (sem reencode)"],
            ["mp3_320", "mp3 320k (reencode)"],
          ];

    li.innerHTML = `
      <img src="${item.thumbnail || ""}" alt="" onerror="this.style.visibility='hidden'" />
      <div class="result-info">
        <div class="title">${escapeHtml(item.title)}</div>
        <div class="artist">${escapeHtml(item.artist)}</div>
        <div class="meta">
          <span class="duration">${formatDuration(item.duration_ms)}</span>
          <span class="bpm">${item.bpm ? `${item.bpm} bpm` : "bpm: calculando..."}</span>
        </div>
      </div>
      <div class="result-actions">
        <button type="button" class="glossy-btn round small preview-btn" title="ouvir prévia">▶</button>
        <select class="quality">
          ${qualityOptions.map(([v, label]) => `<option value="${v}">${label}</option>`).join("")}
        </select>
        <button class="glossy-btn small download-btn">baixar</button>
      </div>
      <div class="status"></div>
    `;

    const btn = li.querySelector(".download-btn");
    const statusEl = li.querySelector(".status");
    const qualitySelect = li.querySelector(".quality");
    const previewBtn = li.querySelector(".preview-btn");
    const bpmEl = li.querySelector(".bpm");

    btn.addEventListener("click", () => startDownload(item, qualitySelect.value, btn, statusEl));
    previewBtn.addEventListener("click", () => togglePreview(item, previewBtn));
    li.addEventListener("click", (evt) => {
      if (evt.target.closest(".result-actions")) return;
      setNowPanel(item, "selecionado");
    });

    resultsEl.appendChild(li);

    if (!item.bpm) queueBpmTask(() => populateBpm(item, bpmEl));
  }
}

async function populateBpm(item, bpmEl) {
  try {
    if (item.source === "spotify" && spotifyAuthenticated) {
      const res = await fetch(`/api/bpm-spotify?track_id=${encodeURIComponent(item.id)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.bpm) {
          bpmEl.textContent = `${data.bpm} bpm`;
          return;
        }
      }
    }

    if (item.source === "spotify" && item.preview_url) {
      const key = `spotify:${item.id}`;
      const res = await fetch(`/api/bpm?key=${encodeURIComponent(key)}&preview_url=${encodeURIComponent(item.preview_url)}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      bpmEl.textContent = data.bpm ? `${data.bpm} bpm` : "bpm: --";
      return;
    }

    let videoUrl = item.url;
    if (item.source === "spotify") {
      const matchId = await resolveYoutubeMatch(item);
      if (!matchId) {
        bpmEl.textContent = "bpm: --";
        return;
      }
      videoUrl = `https://www.youtube.com/watch?v=${matchId}`;
    }

    const key = `${item.source}:${item.id}`;
    const res = await fetch(`/api/bpm-youtube?key=${encodeURIComponent(key)}&video_url=${encodeURIComponent(videoUrl)}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    bpmEl.textContent = data.bpm ? `${data.bpm} bpm` : "bpm: --";
  } catch {
    bpmEl.textContent = "bpm: --";
  }
}

async function resolveYoutubeMatch(item) {
  if (item._matchId) return item._matchId;
  const url = `/api/match?title=${encodeURIComponent(item.title)}&artist=${encodeURIComponent(item.artist)}`;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        item._matchId = (await res.json()).id;
        return item._matchId;
      }
    } catch {
      // servidor ocupado ou reiniciando, tenta de novo
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
  return null;
}

async function togglePreview(item, btn) {
  if (currentPreviewBtn === btn) {
    stopPreview();
    return;
  }
  stopPreview();
  currentPreviewBtn = btn;
  btn.disabled = true;

  let youtubeId = null;
  if (item.source === "spotify" && item.preview_url) {
    const audio = new Audio(item.preview_url);
    audio.addEventListener("ended", stopPreview);
    audio.play();
    currentPreviewMedia = audio;
  } else if (item.source === "youtube") {
    youtubeId = item.id;
  } else {
    btn.textContent = "…";
    youtubeId = await resolveYoutubeMatch(item);
  }

  if (youtubeId) {
    const li = btn.closest(".result-card");
    const frame = document.createElement("iframe");
    frame.className = "yt-embed";
    frame.width = "0";
    frame.height = "0";
    frame.allow = "autoplay";
    frame.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1&controls=0`;
    li.appendChild(frame);
    currentPreviewMedia = frame;
  } else if (!currentPreviewMedia) {
    btn.textContent = "sem prévia";
    btn.disabled = false;
    currentPreviewBtn = null;
    return;
  }

  btn.disabled = false;
  btn.textContent = "■";
}

function stopPreview() {
  if (currentPreviewMedia) {
    if (currentPreviewMedia.tagName === "IFRAME") {
      currentPreviewMedia.remove();
    } else {
      currentPreviewMedia.pause();
    }
  }
  if (currentPreviewBtn) {
    currentPreviewBtn.textContent = "▶";
    currentPreviewBtn.disabled = false;
  }
  currentPreviewMedia = null;
  currentPreviewBtn = null;
}

function resetNowPanel() {
  nowArt.style.backgroundImage = "";
  nowTitle.textContent = "nenhum download ainda";
  nowArtist.textContent = "busque uma música ao lado pra começar";
  nowSource.textContent = " ";
  nowBpm.textContent = " ";
  nowStatus.textContent = "em espera";
  nowStatus.className = "now-status";
  setProgress(false, 0);
}

function setNowPanel(item, statusText, statusClass) {
  nowArt.style.backgroundImage = item.thumbnail ? `url("${item.thumbnail}")` : "";
  nowTitle.textContent = item.title;
  nowArtist.textContent = item.artist || "";
  nowSource.textContent = item.source === "spotify" ? "Spotify · mp3 320k" : "YouTube · áudio original";
  nowBpm.textContent = "";
  nowStatus.textContent = statusText;
  nowStatus.className = `now-status ${statusClass || ""}`.trim();
}

function setProgress(indeterminate, percent) {
  nowFill.classList.toggle("indeterminate", !!indeterminate);
  nowFill.style.width = indeterminate ? "" : `${percent}%`;
}

async function startDownload(item, quality, btn, statusEl) {
  btn.disabled = true;
  statusEl.textContent = "iniciando...";
  statusEl.className = "status";
  setNowPanel(item, "iniciando download...");
  setProgress(true);
  footerMsg.textContent = "baixando...";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: item.source,
        ref: item.url,
        quality,
        title: item.title,
        artist: item.artist,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "erro ao iniciar download");
    const { job_id } = await res.json();
    pollStatus(job_id, btn, statusEl, item, 0);
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status error";
    setNowPanel(item, err.message, "error");
    setProgress(false, 0);
    footerMsg.textContent = "erro no download";
    btn.disabled = false;
  }
}

async function pollStatus(jobId, btn, statusEl, item, attempt) {
  if (attempt >= POLL_MAX_ATTEMPTS) {
    const msg = "download demorou demais e foi cancelado (verifique se o ffmpeg está instalado e no PATH)";
    statusEl.textContent = "tempo esgotado";
    statusEl.className = "status error";
    setNowPanel(item, msg, "error");
    setProgress(false, 0);
    footerMsg.textContent = "download demorou demais";
    btn.disabled = false;
    return;
  }

  let data;
  try {
    const res = await fetch(`/api/download/${jobId}/status`);
    data = await res.json();
  } catch {
    setTimeout(() => pollStatus(jobId, btn, statusEl, item, attempt + 1), POLL_INTERVAL_MS);
    return;
  }

  if (data.status === "done") {
    statusEl.textContent = "pronto";
    statusEl.className = "status done";
    setNowPanel(item, "pronto para baixar", "done");
    if (data.bpm) nowBpm.textContent = `${data.bpm} bpm`;
    setProgress(false, 100);
    footerMsg.textContent = "download concluído";
    window.location.href = `/api/download/${jobId}/file`;
    btn.disabled = false;
    loadStats();
    return;
  }

  if (data.status === "error") {
    statusEl.textContent = data.error || "erro";
    statusEl.className = "status error";
    setNowPanel(item, data.error || "erro no download", "error");
    setProgress(false, 0);
    footerMsg.textContent = "erro no download";
    btn.disabled = false;
    return;
  }

  statusEl.textContent = data.status;
  setNowPanel(item, data.status === "downloading" ? "baixando..." : "na fila...");
  setTimeout(() => pollStatus(jobId, btn, statusEl, item, attempt + 1), POLL_INTERVAL_MS);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}
