const form = document.getElementById("analyze-form");
const startBtn = document.getElementById("start-btn");
const statusPill = document.getElementById("status-pill");
const logOutput = document.getElementById("log-output");
const resultsPanel = document.getElementById("results-panel");
const modeButtons = document.querySelectorAll(".mode-btn");
const moduleWarning = document.getElementById("module-warning");
const contentModuleCheckbox = document.getElementById("mod-content");
const contentCountField = document.getElementById("content-count-field");

let selectedMode = "dry_run";

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    selectedMode = btn.dataset.mode;
  });
});

contentModuleCheckbox.addEventListener("change", () => {
  contentCountField.hidden = !contentModuleCheckbox.checked;
});

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

// --- Onay modalı + toast bildirimi (silme gibi geri alınamaz işlemler için) ---

const confirmModal = document.getElementById("confirm-modal");
const confirmModalMessage = document.getElementById("confirm-modal-message");
const confirmModalCancelBtn = document.getElementById("confirm-modal-cancel");
const confirmModalConfirmBtn = document.getElementById("confirm-modal-confirm");
const toastEl = document.getElementById("toast");

// Belt-and-suspenders: the modal must never be visible on first load,
// regardless of markup/CSS state -- explicitly force it closed once the DOM
// is ready instead of relying solely on the `hidden` attribute in index.html.
document.addEventListener("DOMContentLoaded", () => {
  confirmModal.hidden = true;
});

let toastTimer = null;

function showToast(message, kind = "success") {
  toastEl.textContent = message;
  toastEl.className = `toast toast-${kind}`;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.hidden = true;
  }, 2500);
}

function showConfirmModal(message) {
  confirmModalMessage.textContent = message;
  confirmModal.hidden = false;

  return new Promise((resolve) => {
    function cleanup(result) {
      confirmModal.hidden = true;
      confirmModalConfirmBtn.removeEventListener("click", onConfirm);
      confirmModalCancelBtn.removeEventListener("click", onCancel);
      confirmModal.removeEventListener("click", onOverlayClick);
      resolve(result);
    }
    function onConfirm() {
      cleanup(true);
    }
    function onCancel() {
      cleanup(false);
    }
    function onOverlayClick(e) {
      if (e.target === confirmModal) cleanup(false);
    }
    confirmModalConfirmBtn.addEventListener("click", onConfirm);
    confirmModalCancelBtn.addEventListener("click", onCancel);
    confirmModal.addEventListener("click", onOverlayClick);
  });
}

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

function appendLogLines(container, lines) {
  for (const line of lines) {
    const span = document.createElement("div");
    span.className = `log-line-${line.level}`;
    const time = new Date(line.ts * 1000).toLocaleTimeString();
    span.textContent = `[${time}] ${line.message}`;
    container.appendChild(span);
  }
  if (lines.length) container.scrollTop = container.scrollHeight;
}

// Polls /api/logs + /api/status until the single background job finishes,
// streaming log lines into `logContainer`. Shared by the main analyze form
// and the history panel's "Dinamik Yeni İçerik İskeleti Çıkar" re-trigger,
// since job_manager only ever runs one job at a time regardless of which
// endpoint started it.
function pollJob(logContainer, onDone) {
  let cursor = 0;
  const timer = setInterval(async () => {
    try {
      const [logsRes, statusRes] = await Promise.all([
        fetch(`/api/logs?since=${cursor}`).then((r) => r.json()),
        fetch("/api/status").then((r) => r.json()),
      ]);
      appendLogLines(logContainer, logsRes.logs);
      cursor = logsRes.cursor;
      setStatusPill(statusRes.status);

      if (statusRes.status === "done") {
        clearInterval(timer);
        await onDone(null);
      } else if (statusRes.status === "error") {
        clearInterval(timer);
        appendLogLines(logContainer, [
          { level: "ERROR", ts: Date.now() / 1000, message: statusRes.error || "Bilinmeyen hata" },
        ]);
        await onDone(statusRes.error || "Bilinmeyen hata");
      }
    } catch (err) {
      console.error(err);
    }
  }, 1000);
}

function buildModuleBadges(modulesRun) {
  const labels = {
    market_analysis: "Pazar Analizi",
    pricing: "Fiyatlandırma",
    content_skeletons: "İçerik İskeletleri",
    gap_analysis: "Ekstra Özellik",
  };
  if (!modulesRun) return "";
  return Object.entries(labels)
    .map(([key, label]) => {
      const on = !!modulesRun[key];
      return `<span class="module-badge ${on ? "module-badge-on" : "module-badge-off"}">${label}</span>`;
    })
    .join("");
}

function groupSkeletonsByViral(contentSkeletons) {
  const map = new Map();
  for (const cs of contentSkeletons) {
    const key = cs.source_viral_content_id || "unmatched";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(cs);
  }
  return map;
}

// Shared renderer for both the "just finished" results panel and the
// history panel's project-detail view -- null-safe, so a partial run
// (only some of the 4 modules selected) just skips the missing sections
// instead of throwing on a null field.
function buildResultsHtml(market, viralContents, contentSkeletons) {
  viralContents = viralContents || [];
  contentSkeletons = contentSkeletons || [];
  const skeletonsByViral = groupSkeletonsByViral(contentSkeletons);

  let html = `<div class="module-badges">${buildModuleBadges(market.modules_run)}</div>`;
  let hasAnySection = false;

  if (market.recommended_continent || market.pricing_matrix) {
    hasAnySection = true;
    html += `<div class="results-grid">`;
    if (market.recommended_continent) {
      html += `<div class="card"><h3>Önerilen Kıta</h3><p class="big-value">${escapeHtml(market.recommended_continent)}</p></div>`;
    }
    if (market.pricing_matrix) {
      html += `<div class="card"><h3>Önerilen Giriş Fiyatı</h3><p class="big-value">${escapeHtml(String(market.pricing_matrix.recommended_entry_price))}</p></div>`;
    }
    html += `</div>`;
  }

  if (market.top_3_countries && market.top_3_countries.length) {
    hasAnySection = true;
    html += `<h3>İlk 3 Ülke</h3><table class="data-table"><thead><tr><th>#</th><th>Ülke</th><th>PPP Durumu</th><th>Gerekçe</th></tr></thead><tbody>`;
    for (const c of market.top_3_countries) {
      html += `<tr><td>${c.rank}</td><td>${escapeHtml(c.country)}</td><td>${escapeHtml(c.ppp_status)}</td><td>${escapeHtml(c.rationale)}</td></tr>`;
    }
    html += `</tbody></table>`;
  }

  if (market.pricing_matrix) {
    hasAnySection = true;
    const pm = market.pricing_matrix;
    html += `<h3>Fiyat Matrisi</h3><table class="data-table"><thead><tr><th>Min</th><th>Ortalama</th><th>Maks</th><th>Önerilen Giriş</th><th>Gerekçe</th></tr></thead><tbody>`;
    html += `<tr><td>${pm.min_price}</td><td>${pm.avg_price}</td><td>${pm.max_price}</td><td>${pm.recommended_entry_price}</td><td>${escapeHtml(pm.rationale)}</td></tr>`;
    html += `</tbody></table>`;
  }

  if (market.strategic_value_adds && market.strategic_value_adds.length) {
    hasAnySection = true;
    html += `<h3>Stratejik Ek Değer Önerileri</h3><table class="data-table"><thead><tr><th>Rakip Zayıflığı</th><th>Önerilen Özellik</th></tr></thead><tbody>`;
    for (const va of market.strategic_value_adds) {
      html += `<tr><td>${escapeHtml(va.competitor_weakness)}</td><td>${escapeHtml(va.recommended_feature)}</td></tr>`;
    }
    html += `</tbody></table>`;
  }

  if (viralContents.length) {
    hasAnySection = true;
    html += `<h3>Viral İçerik Anatomi Analizi &amp; İçerik İskeletleri</h3><div class="viral-grid">`;
    for (const vc of viralContents) {
      const tiers = (skeletonsByViral.get(vc.id) || []).slice().sort((a, b) => a.tier_type - b.tier_type);
      html += `<div class="viral-card">
        <span class="platform-tag">${escapeHtml(vc.platform)}</span>
        <h4>${escapeHtml(vc.competitor_name)}</h4>
        <dl>
          <dt>Hook (0-3sn)</dt><dd>${escapeHtml(vc.hook_analysis)}</dd>
          <dt>Intro (3-7sn)</dt><dd>${escapeHtml(vc.intro_and_problem)}</dd>
          <dt>Body (7-25sn)</dt><dd>${escapeHtml(vc.body_and_value)}</dd>
          <dt>CTA (25-30sn)</dt><dd>${escapeHtml(vc.call_to_action)}</dd>
          <dt>Özet</dt><dd>${escapeHtml(vc.overall_summary)}</dd>
        </dl>`;
      if (tiers.length) {
        html += `<div class="tier-list">`;
        for (const t of tiers) {
          const sd = t.skeleton_data || {};
          html += `<div class="tier-card tier-${t.tier_type}">
            <span class="tier-tag">Tier ${t.tier_type}: ${escapeHtml(t.tier_label)}</span>
            <dl>
              <dt>Hook</dt><dd>${escapeHtml(sd.hook)}</dd>
              <dt>Intro</dt><dd>${escapeHtml(sd.intro)}</dd>
              <dt>Body</dt><dd>${escapeHtml(sd.body)}</dd>
              <dt>CTA</dt><dd>${escapeHtml(sd.cta)}</dd>
            </dl>
          </div>`;
        }
        html += `</div>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  }

  if (!hasAnySection) {
    html += `<p class="muted">Bu proje için henüz hiçbir modül sonucu yok.</p>`;
  }

  return html;
}

async function loadResults() {
  const res = await fetch("/api/results").then((r) => r.json());
  if (!res.available) return;

  resultsPanel.hidden = false;
  document.getElementById("results-body").innerHTML = buildResultsHtml(
    res.market_analysis,
    res.viral_contents,
    res.content_skeletons
  );
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const modules = {
    run_market_analysis: document.getElementById("mod-market").checked,
    run_pricing: document.getElementById("mod-pricing").checked,
    run_content_skeletons: document.getElementById("mod-content").checked,
    run_gap_analysis: document.getElementById("mod-gap").checked,
  };
  if (!Object.values(modules).some(Boolean)) {
    moduleWarning.hidden = false;
    return;
  }
  moduleWarning.hidden = true;

  const payload = {
    project_description: document.getElementById("project-description").value.trim(),
    project_name: document.getElementById("project-name").value.trim() || null,
    mode: selectedMode,
    max_competitors: parseInt(document.getElementById("max-competitors").value, 10) || 10,
    content_skeleton_count: parseInt(document.getElementById("content-skeleton-count").value, 10) || 3,
    ...modules,
  };

  logOutput.textContent = "";
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
    appendLogLines(logOutput, [{ level: "ERROR", ts: Date.now() / 1000, message: err.message }]);
    setStatusPill("error");
    startBtn.disabled = false;
    return;
  }

  pollJob(logOutput, async () => {
    startBtn.disabled = false;
    await loadResults();
  });
});

// --- Geçmiş Projelerim ------------------------------------------------

const viewTabs = document.querySelectorAll(".view-tab");
const viewAnalyze = document.getElementById("view-analyze");
const viewHistory = document.getElementById("view-history");
const historyList = document.getElementById("history-list");
const historyDetailPanel = document.getElementById("history-detail-panel");
const historyResults = document.getElementById("history-results");
const historyLogOutput = document.getElementById("history-log-output");
const historyRetriggerBtn = document.getElementById("history-retrigger-btn");
const historySkeletonCount = document.getElementById("history-skeleton-count");

let currentHistoryProjectId = null;

viewTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    viewTabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const view = tab.dataset.view;
    viewAnalyze.hidden = view !== "analyze";
    viewHistory.hidden = view !== "history";
    if (view === "history") loadProjectList();
  });
});

async function loadProjectList() {
  const res = await fetch("/api/projects").then((r) => r.json());
  historyList.innerHTML = "";
  if (!res.projects || !res.projects.length) {
    historyList.innerHTML = `<p class="muted">Henüz kaydedilmiş bir proje yok.</p>`;
    return;
  }
  for (const p of res.projects) {
    const item = document.createElement("div");
    item.className = "history-item";

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.className = "history-item-open";
    const date = p.created_at ? new Date(p.created_at).toLocaleString("tr-TR") : "";
    openBtn.innerHTML = `
      <strong>${escapeHtml(p.project_name)}</strong>
      <span class="muted">${escapeHtml(p.recommended_continent || "-")} · ${escapeHtml(date)}</span>
      <div class="module-badges">${buildModuleBadges(p.modules_run)}</div>`;
    openBtn.addEventListener("click", () => openProjectDetail(p.id));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "history-item-delete";
    deleteBtn.title = "Projeyi sil";
    deleteBtn.setAttribute("aria-label", "Projeyi sil");
    deleteBtn.textContent = "🗑";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteProject(p.id, p.project_name);
    });

    item.appendChild(openBtn);
    item.appendChild(deleteBtn);
    historyList.appendChild(item);
  }
}

async function deleteProject(projectId, projectName) {
  const confirmed = await showConfirmModal(
    `"${projectName}" projesini silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.`
  );
  if (!confirmed) return;

  try {
    const res = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Silme işlemi başarısız oldu.");
    }
  } catch (err) {
    showToast(err.message, "error");
    return;
  }

  if (currentHistoryProjectId === projectId) {
    currentHistoryProjectId = null;
    historyDetailPanel.hidden = true;
    historyResults.innerHTML = "";
  }

  showToast("Proje silindi.", "success");
  await loadProjectList();
}

async function openProjectDetail(projectId) {
  const res = await fetch(`/api/projects/${projectId}`).then((r) => r.json());
  if (!res.available) return;

  currentHistoryProjectId = projectId;
  historyDetailPanel.hidden = false;
  historyLogOutput.hidden = true;
  historyLogOutput.textContent = "";
  historyResults.innerHTML = buildResultsHtml(
    res.market_analysis,
    res.viral_contents,
    res.content_skeletons
  );
}

historyRetriggerBtn.addEventListener("click", async () => {
  if (!currentHistoryProjectId) return;

  const count = parseInt(historySkeletonCount.value, 10) || 3;
  historyRetriggerBtn.disabled = true;
  historyLogOutput.hidden = false;
  historyLogOutput.textContent = "";
  setStatusPill("running");

  try {
    const res = await fetch(`/api/projects/${currentHistoryProjectId}/content-skeletons`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "İstek başarısız oldu.");
    }
  } catch (err) {
    appendLogLines(historyLogOutput, [{ level: "ERROR", ts: Date.now() / 1000, message: err.message }]);
    setStatusPill("error");
    historyRetriggerBtn.disabled = false;
    return;
  }

  pollJob(historyLogOutput, async () => {
    historyRetriggerBtn.disabled = false;
    await openProjectDetail(currentHistoryProjectId);
  });
});

(async function init() {
  const statusRes = await fetch("/api/status").then((r) => r.json());
  if (statusRes.status === "running") {
    startBtn.disabled = true;
    setStatusPill("running");
    pollJob(logOutput, async () => {
      startBtn.disabled = false;
      await loadResults();
    });
  } else if (statusRes.status === "done") {
    setStatusPill("done");
    await loadResults();
  }
})();
