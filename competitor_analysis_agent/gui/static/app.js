const form = document.getElementById("analyze-form");
const startBtn = document.getElementById("start-btn");
const statusPill = document.getElementById("status-pill");
const logOutput = document.getElementById("log-output");
const resultsPanel = document.getElementById("results-panel");
const modeButtons = document.querySelectorAll(".mode-btn");

let selectedMode = "dry_run";
let logCursor = 0;
let pollTimer = null;

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    selectedMode = btn.dataset.mode;
  });
});

function setStatusPill(status) {
  statusPill.className = "pill";
  const map = {
    idle: ["Hazır", "pill-idle"],
    running: ["Çalışıyor…", "pill-running"],
    done: ["Tamamlandı", "pill-done"],
    error: ["Hata", "pill-error"],
  };
  const [label, cls] = map[status] || map.idle;
  statusPill.textContent = label;
  statusPill.classList.add(cls);
}

function appendLogLines(lines) {
  for (const line of lines) {
    const span = document.createElement("div");
    span.className = `log-line-${line.level}`;
    const time = new Date(line.ts * 1000).toLocaleTimeString();
    span.textContent = `[${time}] ${line.message}`;
    logOutput.appendChild(span);
  }
  if (lines.length) logOutput.scrollTop = logOutput.scrollHeight;
}

async function pollLogsAndStatus() {
  try {
    const [logsRes, statusRes] = await Promise.all([
      fetch(`/api/logs?since=${logCursor}`).then((r) => r.json()),
      fetch("/api/status").then((r) => r.json()),
    ]);

    appendLogLines(logsRes.logs);
    logCursor = logsRes.cursor;

    setStatusPill(statusRes.status);

    if (statusRes.status === "done") {
      clearInterval(pollTimer);
      startBtn.disabled = false;
      await loadResults();
    } else if (statusRes.status === "error") {
      clearInterval(pollTimer);
      startBtn.disabled = false;
      appendLogLines([{ level: "ERROR", ts: Date.now() / 1000, message: statusRes.error || "Bilinmeyen hata" }]);
    }
  } catch (err) {
    console.error(err);
  }
}

async function loadResults() {
  const res = await fetch("/api/results").then((r) => r.json());
  if (!res.available) return;

  resultsPanel.hidden = false;
  const market = res.market_analysis;
  const viralContents = res.viral_contents || [];

  document.getElementById("res-continent").textContent = market.recommended_continent;
  document.getElementById("res-entry-price").textContent = market.pricing_matrix.recommended_entry_price;

  const countriesBody = document.getElementById("res-countries");
  countriesBody.innerHTML = "";
  for (const c of market.top_3_countries) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${c.rank}</td><td>${c.country}</td><td>${c.ppp_status}</td><td>${c.rationale}</td>`;
    countriesBody.appendChild(tr);
  }

  const pm = market.pricing_matrix;
  const pricingBody = document.getElementById("res-pricing");
  pricingBody.innerHTML = `<tr><td>${pm.min_price}</td><td>${pm.avg_price}</td><td>${pm.max_price}</td><td>${pm.recommended_entry_price}</td><td>${pm.rationale}</td></tr>`;

  const valueAddsBody = document.getElementById("res-value-adds");
  valueAddsBody.innerHTML = "";
  for (const va of market.strategic_value_adds) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${va.competitor_weakness}</td><td>${va.recommended_feature}</td>`;
    valueAddsBody.appendChild(tr);
  }

  const viralGrid = document.getElementById("res-viral");
  viralGrid.innerHTML = "";
  for (const vc of viralContents) {
    const card = document.createElement("div");
    card.className = "viral-card";
    card.innerHTML = `
      <span class="platform-tag">${vc.platform}</span>
      <h4>${vc.competitor_name}</h4>
      <dl>
        <dt>Hook (0-3sn)</dt><dd>${vc.hook_analysis}</dd>
        <dt>Intro (3-7sn)</dt><dd>${vc.intro_and_problem}</dd>
        <dt>Body (7-25sn)</dt><dd>${vc.body_and_value}</dd>
        <dt>CTA (25-30sn)</dt><dd>${vc.call_to_action}</dd>
        <dt>Özet</dt><dd>${vc.overall_summary}</dd>
      </dl>`;
    viralGrid.appendChild(card);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    project_description: document.getElementById("project-description").value.trim(),
    project_name: document.getElementById("project-name").value.trim() || null,
    mode: selectedMode,
    max_competitors: parseInt(document.getElementById("max-competitors").value, 10) || 10,
  };

  logOutput.textContent = "";
  logCursor = 0;
  resultsPanel.hidden = true;
  startBtn.disabled = true;
  setStatusPill("running");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "İstek başarısız oldu.");
    }
  } catch (err) {
    appendLogLines([{ level: "ERROR", ts: Date.now() / 1000, message: err.message }]);
    setStatusPill("error");
    startBtn.disabled = false;
    return;
  }

  pollTimer = setInterval(pollLogsAndStatus, 1000);
});

(async function init() {
  const statusRes = await fetch("/api/status").then((r) => r.json());
  if (statusRes.status === "running") {
    startBtn.disabled = true;
    setStatusPill("running");
    pollTimer = setInterval(pollLogsAndStatus, 1000);
  } else if (statusRes.status === "done") {
    setStatusPill("done");
    await loadResults();
  }
})();
