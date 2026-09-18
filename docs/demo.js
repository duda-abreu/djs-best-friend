const API = "https://itunes.apple.com/search";

const form = document.getElementById("search-form");
const queryEl = document.getElementById("query");
const limitEl = document.getElementById("result-limit");
const resultsEl = document.getElementById("results");
const titleEl = document.getElementById("results-title");
const footerMsg = document.getElementById("footer-msg");
const footerSep = document.getElementById("footer-sep");

function setFooter(text) {
  footerMsg.textContent = text;
  footerSep.hidden = !text;
}

const nowArt = document.getElementById("now-art");
const nowTitle = document.getElementById("now-title");
const nowArtist = document.getElementById("now-artist");
const nowSource = document.getElementById("now-source");
const nowFill = document.getElementById("now-fill");
const nowStatus = document.getElementById("now-status");
const nowLink = document.getElementById("now-link");

const audio = new Audio();
let playingCard = null;

const PLAY_ICON = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>';
const PAUSE_ICON = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>';

function isHttps(url) {
  return typeof url === "string" && url.startsWith("https://");
}

function formatDuration(ms) {
  const total = Math.round(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function hiResArt(url) {
  return url.replace("100x100bb", "600x600bb");
}

function setHint(text) {
  const li = document.createElement("li");
  li.className = "empty-hint";
  li.textContent = text;
  resultsEl.replaceChildren(li);
}

function setPlayIcon(card, playing) {
  card.querySelector(".play-btn").innerHTML = playing ? PAUSE_ICON : PLAY_ICON;
  card.classList.toggle("playing", playing);
}

function showNow(track) {
  nowTitle.textContent = track.trackName;
  nowArtist.textContent = track.artistName;
  nowSource.textContent = track.collectionName || "";
  nowArt.style.backgroundImage = isHttps(track.artworkUrl100) ? `url("${hiResArt(track.artworkUrl100)}")` : "";
  if (isHttps(track.trackViewUrl)) {
    nowLink.href = track.trackViewUrl;
    nowLink.hidden = false;
  } else {
    nowLink.hidden = true;
  }
}

function play(track, card) {
  if (playingCard === card && !audio.paused) {
    audio.pause();
    return;
  }
  if (playingCard && playingCard !== card) {
    setPlayIcon(playingCard, false);
  }
  playingCard = card;
  audio.src = track.previewUrl;
  audio.play().catch(() => {
    nowStatus.textContent = "não foi possível tocar a prévia";
    nowStatus.className = "now-status error";
  });
  showNow(track);
}

audio.addEventListener("play", () => {
  if (playingCard) setPlayIcon(playingCard, true);
  nowStatus.textContent = "tocando prévia de 30s";
  nowStatus.className = "now-status done";
});

audio.addEventListener("pause", () => {
  if (playingCard) setPlayIcon(playingCard, false);
  if (!audio.ended) nowStatus.textContent = "pausado";
});

audio.addEventListener("ended", () => {
  nowFill.style.width = "0%";
  nowStatus.textContent = "fim da prévia";
});

audio.addEventListener("timeupdate", () => {
  if (audio.duration) nowFill.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
});

function renderTrack(track) {
  const li = document.createElement("li");
  li.className = "result-card";

  const img = document.createElement("img");
  img.alt = "";
  img.loading = "lazy";
  if (isHttps(track.artworkUrl100)) img.src = track.artworkUrl100;

  const info = document.createElement("div");
  info.className = "result-info";
  const title = document.createElement("div");
  title.className = "title";
  title.textContent = track.trackName;
  const artist = document.createElement("div");
  artist.className = "artist";
  artist.textContent = track.artistName;
  const meta = document.createElement("div");
  meta.className = "meta";
  const duration = document.createElement("span");
  duration.textContent = formatDuration(track.trackTimeMillis || 0);
  meta.append(duration);
  if (track.bpm) {
    const bpm = document.createElement("span");
    bpm.textContent = `${track.bpm} bpm`;
    meta.append(bpm);
  }
  info.append(title, artist, meta);

  const actions = document.createElement("div");
  actions.className = "result-actions";

  const playBtn = document.createElement("button");
  playBtn.type = "button";
  playBtn.className = "glossy-btn round play-btn";
  playBtn.title = "ouvir prévia";
  playBtn.setAttribute("aria-label", "ouvir prévia");
  playBtn.innerHTML = PLAY_ICON;
  playBtn.disabled = !isHttps(track.previewUrl);
  actions.append(playBtn);

  if (isHttps(track.trackViewUrl)) {
    const link = document.createElement("a");
    link.className = "glossy-btn small";
    link.href = track.trackViewUrl;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Apple Music";
    link.addEventListener("click", (e) => e.stopPropagation());
    actions.append(link);
  }

  li.append(img, info, actions);
  li.addEventListener("click", () => {
    if (isHttps(track.previewUrl)) play(track, li);
  });
  return li;
}

let currentView = { type: "trending" };
let trendingData = null;

async function loadTrending() {
  currentView = { type: "trending" };
  titleEl.textContent = "em alta essa semana";
  try {
    if (!trendingData) {
      setHint("carregando...");
      const resp = await fetch("trending.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error(`erro ${resp.status}`);
      trendingData = await resp.json();
    }
    const tracks = trendingData.tracks.slice(0, Number(limitEl.value));
    resultsEl.replaceChildren(...tracks.map(renderTrack));
    setFooter("");
  } catch {
    titleEl.textContent = "resultados";
    setHint("digite o nome de uma música ou artista e clique em buscar.");
  }
}

async function search(term) {
  currentView = { type: "search", term };
  const url = new URL(API);
  url.search = new URLSearchParams({
    term,
    media: "music",
    entity: "song",
    limit: limitEl.value,
    country: "BR",
  });

  setHint("buscando...");
  setFooter("buscando...");
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`erro ${resp.status}`);
    const data = await resp.json();
    const tracks = data.results.filter((t) => t.trackName);

    titleEl.textContent = `resultados para "${term}"`;
    if (!tracks.length) {
      setHint("nenhum resultado encontrado.");
      setFooter("sem resultados");
      return;
    }
    resultsEl.replaceChildren(...tracks.map(renderTrack));
    setFooter(`${tracks.length} resultados`);
  } catch (err) {
    setHint(`não foi possível buscar: ${err.message}`);
    setFooter("erro na busca");
  }
}

limitEl.addEventListener("change", () => {
  if (currentView.type === "search") search(currentView.term);
  else loadTrending();
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const term = queryEl.value.trim();
  if (term) search(term);
});

document.getElementById("home-link").addEventListener("click", () => {
  audio.pause();
  audio.removeAttribute("src");
  playingCard = null;
  queryEl.value = "";
  nowTitle.textContent = "nenhuma faixa tocando";
  nowArtist.textContent = "busque uma música ao lado pra começar";
  nowSource.innerHTML = "&nbsp;";
  nowArt.style.backgroundImage = "";
  nowFill.style.width = "0%";
  nowStatus.textContent = "em espera";
  nowStatus.className = "now-status";
  nowLink.hidden = true;
  loadTrending();
});

function tickClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

tickClock();
setInterval(tickClock, 30000);
loadTrending();
