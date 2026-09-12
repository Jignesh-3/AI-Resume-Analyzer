let selectedFile = null;
let activePreset = "backend_python";
let currentMatrixData = [];
let currentFilter = "ALL";

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  setupPresets();
  setupFileInput();
  setupAuditAction();
  setupMatrixFilterTabs();
});

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    const countEl = document.getElementById("audit-count");
    if (countEl) countEl.innerText = data.total_audits ?? 18;
  } catch (e) {
    const countEl = document.getElementById("audit-count");
    if (countEl) countEl.innerText = "18";
  }
}

function setupPresets() {
  const buttons = document.querySelectorAll(".preset-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activePreset = btn.getAttribute("data-preset");
    });
  });
}

function setupFileInput() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileLabel = document.getElementById("file-label");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      selectedFile = e.target.files[0];
      if (fileLabel) {
        fileLabel.innerHTML = `Selected: <strong style="color: var(--accent);">${selectedFile.name}</strong>`;
      }
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--accent)";
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "var(--surface-border)";
  });
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--surface-border)";
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      selectedFile = e.dataTransfer.files[0];
      if (fileLabel) {
        fileLabel.innerHTML = `Selected: <strong style="color: var(--accent);">${selectedFile.name}</strong>`;
      }
    }
  });
}

function setupAuditAction() {
  const btn = document.getElementById("analyze-btn");
  if (!btn) return;

  btn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      alert("Please upload a PDF resume first.");
      return;
    }

    btn.disabled = true;
    btn.innerText = "Auditing Architectural Causality with Gemini...";

    const formData = new FormData();
    formData.append("resume_file", selectedFile);
    formData.append("preset_key", activePreset);
    const jdVal = document.getElementById("jd-input")?.value || "";
    formData.append("job_description", jdVal);

    try {
      const res = await fetch("/api/analyze", { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Audit execution failed");
      }
      const report = await res.json();
      renderDashboard(report);
      fetchStats();
    } catch (err) {
      alert("Error during audit: " + err.message);
    } finally {
      btn.disabled = false;
      btn.innerText = "Execute Bar-Raiser Audit";
    }
  });
}

function setupMatrixFilterTabs() {
  const tabs = document.querySelectorAll("#matrix-tabs .tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentFilter = tab.getAttribute("data-filter") || "ALL";
      renderMatrixRows();
    });
  });
}

function renderDashboard(data) {
  document.getElementById("results-container").classList.remove("hidden");

  // 1. Top 4 KPI Metrics
  document.getElementById("assessed-level").innerText = data.candidate_level_assessed || "Software Engineer";
  const senioritySub = document.getElementById("seniority-context");
  if (senioritySub) senioritySub.innerText = data.seniority_subtext || "Engineering Depth";

  document.getElementById("match-score").innerText = data.target_match_percentage ?? 0;
  document.getElementById("xyz-score").innerText = data.xyz_adherence_percentage ?? 0;
  document.getElementById("unbacked-count").innerText = data.unbacked_skills_count ?? (data.overclaimed_buzzwords?.length || 0);

  // 2. Executive Technical Assessment
  document.getElementById("fit-summary").innerText = data.technical_fit_summary || "";

  // 3. Overclaimed Buzzwords Banner
  const buzzBox = document.getElementById("buzzword-radar");
  const buzzList = document.getElementById("buzzwords-list");
  buzzList.innerHTML = "";
  if (data.overclaimed_buzzwords && data.overclaimed_buzzwords.length > 0) {
    buzzBox.classList.remove("hidden");
    data.overclaimed_buzzwords.forEach(bw => {
      const tag = document.createElement("span");
      tag.className = "danger-tag";
      tag.innerText = bw;
      buzzList.appendChild(tag);
    });
  } else {
    buzzBox.classList.add("hidden");
  }

  // 4. Matrix Data & Filtering
  currentMatrixData = data.skill_matrix || [];
  updateMatrixCounts();
  renderMatrixRows();

  // 5. Bullet-Level Causality & XYZ Refactors
  renderBulletAudits(data.bullet_audits || []);

  // 6. Dedicated Hiring Manager Claim Interrogations
  renderInterrogations(data.hiring_manager_interrogations || []);

  document.getElementById("results-container").scrollIntoView({ behavior: "smooth" });
}

function normalizeStatus(status) {
  return (status || "").toString().trim().toUpperCase();
}

function updateMatrixCounts() {
  document.getElementById("count-all").innerText = currentMatrixData.length;
  document.getElementById("count-verified").innerText = currentMatrixData.filter(
    i => normalizeStatus(i.status) === "VERIFIED"
  ).length;
  document.getElementById("count-surface").innerText = currentMatrixData.filter(
    i => normalizeStatus(i.status) === "SURFACE"
  ).length;
  document.getElementById("count-missing").innerText = currentMatrixData.filter(
    i => normalizeStatus(i.status) === "MISSING"
  ).length;
}

function renderMatrixRows() {
  const matrixBody = document.getElementById("skill-matrix-body");
  matrixBody.innerHTML = "";

  const filtered = currentFilter === "ALL" 
    ? currentMatrixData 
    : currentMatrixData.filter(i => normalizeStatus(i.status) === currentFilter);

  if (filtered.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No skills found under the '${currentFilter}' filter.</td>`;
    matrixBody.appendChild(tr);
    return;
  }

  filtered.forEach(item => {
    const normStatus = normalizeStatus(item.status);
    const normImportance = (item.importance || "PREFERRED").toString().trim().toUpperCase();

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="tech-name">${escapeHtml(item.skill)}</td>
      <td class="domain-name">${escapeHtml(item.domain_category || "General")}</td>
      <td><span class="importance-pill importance-${normImportance}">${normImportance}</span></td>
      <td><span class="status-pill status-${normStatus}">${normStatus}</span></td>
      <td style="color: #cbd5e1; font-size: 0.8rem; line-height: 1.45;">${escapeHtml(item.evidence)}</td>
    `;
    matrixBody.appendChild(tr);
  });
}

function renderBulletAudits(bullets) {
  const bulletsContainer = document.getElementById("bullet-audits-list");
  bulletsContainer.innerHTML = "";

  bullets.forEach(b => {
    // Sanitize any raw numeric OCR tags/prefixes
    const cleanProject = (b.project_context || "Engineering Experience")
      .replace(/^\s*[-#\d]+\s*/, "")
      .trim();

    const div = document.createElement("div");
    div.className = "bullet-item";

    const questionsHtml = (b.possible_interview_questions || [])
      .map(q => `<li><strong>Interviewer Trap:</strong> ${escapeHtml(q)}</li>`).join("");

    div.innerHTML = `
      <div class="refactor-meta-row">
        <div class="diagnostic-group">
          <span class="diagnostic-tag">${escapeHtml(b.diagnostic_tag || "Missing Metric")}</span>
          <span class="coherence-tag">Coherence: <strong>${b.technical_coherence_score || 5}/10</strong></span>
        </div>
        <div class="copy-toolbar">
          <button type="button" class="copy-pill copy-text-btn">Copy Refactor</button>
          <button type="button" class="copy-pill copy-latex-btn">Copy LaTeX</button>
        </div>
      </div>

      <div class="project-context-title">${escapeHtml(cleanProject)}</div>

      <div class="diff-box">
        <div class="diff-red"><span class="diff-sign">-</span> <span>${escapeHtml(b.original_text)}</span></div>
        <div class="diff-green"><span class="diff-sign">+</span> <span>${escapeHtml(b.suggested_diff_rewrite)}</span></div>
      </div>

      <p class="critique"><strong>Bar-Raiser Critique:</strong> ${escapeHtml(b.critique)}</p>

      ${b.possible_interview_questions && b.possible_interview_questions.length > 0 ? `
        <div class="trap-card">
          <div class="trap-title">REVERSE INTERVIEW PREP MATRIX</div>
          <ul style="padding-left: 1.2rem; margin: 0.3rem 0;">${questionsHtml}</ul>
          ${b.winning_response_formula ? `<p class="winning-formula"><strong>Winning Formula:</strong> ${escapeHtml(b.winning_response_formula)}</p>` : ""}
        </div>
      ` : ""}
    `;

    // Clipboard event listeners with state toggles
    const textBtn = div.querySelector(".copy-text-btn");
    const latexBtn = div.querySelector(".copy-latex-btn");

    textBtn.addEventListener("click", () => copyToClipboard(b.suggested_diff_rewrite, textBtn, "Copied Refactor!"));
    latexBtn.addEventListener("click", () => copyToClipboard(formatAsLatex(b.suggested_diff_rewrite), latexBtn, "Copied LaTeX!"));

    bulletsContainer.appendChild(div);
  });
}

function renderInterrogations(questions) {
  const deck = document.getElementById("interrogation-deck");
  if (!deck) return;
  deck.innerHTML = "";

  if (!questions || questions.length === 0) {
    deck.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No technical interrogation questions generated for this profile.</p>`;
    return;
  }

  questions.forEach((q, idx) => {
    const item = document.createElement("div");
    item.className = "interrogation-item";
    item.innerHTML = `
      <span class="q-badge">Q${idx + 1}</span>
      <p class="q-text">${escapeHtml(q)}</p>
    `;
    deck.appendChild(item);
  });
}

function copyToClipboard(text, btn, feedbackMsg) {
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerText;
    btn.innerText = feedbackMsg;
    btn.style.color = "var(--accent)";
    btn.style.borderColor = "var(--accent)";
    setTimeout(() => {
      btn.innerText = original;
      btn.style.color = "";
      btn.style.borderColor = "";
    }, 1800);
  });
}

function formatAsLatex(text) {
  return `\\item ${text.replace(/&/g, "\\&").replace(/%/g, "\\%")}`;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}