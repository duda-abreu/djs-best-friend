const form = document.getElementById("search-form");
const resultsEl = document.getElementById("results");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = document.getElementById("query").value.trim();
  const source = document.getElementById("source").value;
  if (!query) return;

  resultsEl.innerHTML = "<li>Buscando...</li>";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&source=${source}`);
    if (!res.ok) throw new Error((await res.json()).detail || "erro na busca");
    const items = await res.json();
    renderResults(items);
  } catch (err) {
    resultsEl.innerHTML = `<li>Erro: ${err.message}</li>`;
  }
});

function renderResults(items) {
  resultsEl.innerHTML = "";
  if (items.length === 0) {
    resultsEl.innerHTML = "<li>Nenhum resultado encontrado.</li>";
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
      </div>
      <div class="result-actions">
        <select class="quality">
          ${qualityOptions.map(([v, label]) => `<option value="${v}">${label}</option>`).join("")}
        </select>
        <button class="download-btn">Baixar</button>
      </div>
      <div class="status"></div>
    `;

    const btn = li.querySelector(".download-btn");
    const statusEl = li.querySelector(".status");
    const qualitySelect = li.querySelector(".quality");

    btn.addEventListener("click", () => startDownload(item, qualitySelect.value, btn, statusEl));

    resultsEl.appendChild(li);
  }
}

async function startDownload(item, quality, btn, statusEl) {
  btn.disabled = true;
  statusEl.textContent = "iniciando...";
  statusEl.className = "status";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: item.source, ref: item.url, quality }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "erro ao iniciar download");
    const { job_id } = await res.json();
    pollStatus(job_id, btn, statusEl);
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status error";
    btn.disabled = false;
  }
}

async function pollStatus(jobId, btn, statusEl) {
  const res = await fetch(`/api/download/${jobId}/status`);
  const data = await res.json();

  if (data.status === "done") {
    statusEl.textContent = "pronto";
    statusEl.className = "status done";
    window.location.href = `/api/download/${jobId}/file`;
    btn.disabled = false;
    return;
  }

  if (data.status === "error") {
    statusEl.textContent = data.error || "erro";
    statusEl.className = "status error";
    btn.disabled = false;
    return;
  }

  statusEl.textContent = data.status;
  setTimeout(() => pollStatus(jobId, btn, statusEl), 1500);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}
