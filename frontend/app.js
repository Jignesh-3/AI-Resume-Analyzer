let selectedFile = null;
let activePreset = "backend_python";

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  setupPresets();
  setupFileInput();
  setupAuditAction();
});

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    const countEl = document.getElementById("audit-count");
    if (countEl) countEl.innerText = data.total_audits ?? 14;
  } catch (e) {
    const countEl = document.getElementById("audit-count");
    if (countEl) countEl.innerText = "14";
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
    btn.innerText = "Interrogating Claims & Causality (auditing with Gemini)...";

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

function renderDashboard(data) {
  document.getElementById("results-container").classList.remove("hidden");
  document.getElementById("assessed-level").innerText = data.candidate_level_assessed || "Software Engineer";
  document.getElementById("match-score").innerText = data.target_match_percentage ?? 0;
  document.getElementById("fit-summary").innerText = data.technical_fit_summary || "";

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

  const matrixBody = document.getElementById("skill-matrix-body");
  matrixBody.innerHTML = "";
  (data.skill_matrix || []).forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${item.skill}</strong></td>
      <td>${item.domain_category}</td>
      <td><span class="status-pill status-${item.status}">${item.status}</span></td>
      <td>${item.evidence}</td>
    `;
    matrixBody.appendChild(tr);
  });

  const bulletsContainer = document.getElementById("bullet-audits-list");
  bulletsContainer.innerHTML = "";
  (data.bullet_audits || []).forEach(b => {
    const div = document.createElement("div");
    div.className = "bullet-item";

    const questionsHtml = (b.possible_interview_questions || [])
      .map(q => `<li><strong>Interviewer Trap:</strong> ${q}</li>`).join("");

    const escaped = (b.suggested_diff_rewrite || "").replace(/'/g, "\\'");

    div.innerHTML = `
      <div class="diff-box">
        <div class="diff-red">- ${b.original_text}</div>
        <div class="diff-green">+ ${b.suggested_diff_rewrite}</div>
      </div>
      <div class="copy-toolbar">
        <button type="button" class="copy-pill" onclick="copyText('${escaped}')">Copy Text</button>
        <button type="button" class="copy-pill" onclick="copyLatex('${escaped}')">Copy LaTeX</button>
      </div>
      <p class="critique">${b.critique}</p>
      <div class="trap-card">
        <div class="trap-title">REVERSE INTERVIEW PREP MATRIX</div>
        <ul style="padding-left: 1.2rem; margin: 0.3rem 0;">${questionsHtml}</ul>
        ${b.winning_response_formula ? `<p class="winning-formula"><strong>Winning Formula:</strong> ${b.winning_response_formula}</p>` : ""}
      </div>
    `;
    bulletsContainer.appendChild(div);
  });

  document.getElementById("results-container").scrollIntoView({ behavior: "smooth" });
}

window.copyText = function(text) {
  navigator.clipboard.writeText(text);
  alert("Copied rewrite to clipboard!");
};

window.copyLatex = function(text) {
  navigator.clipboard.writeText("\\item " + text);
  alert("Copied LaTeX snippet to clipboard!");
};