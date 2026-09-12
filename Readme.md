# ⚡ Bar-Raiser: AI Resume & Architectural Causality Engine

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini_Flash-8E75B2?style=flat-square&logo=google)](https://ai.google.dev/)
[![Pydantic V2](https://img.shields.io/badge/Validation-Pydantic_v2-E92063?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

An asynchronous, production-grade technical evaluation engine that moves beyond simple keyword matching. Built for engineering candidates and hiring teams, **Bar-Raiser** ingests PDF resumes, cross-references claims against target role archetypes, audits technical causality (Google XYZ format), and generates technical interrogation questions designed for deep systems architecture interviews.

---

## 🎯 The Problem Solved

Standard Applicant Tracking Systems (ATS) rely on shallow keyword indexing, encouraging candidates to keyword-stuff without demonstrating depth. Conversely, engineering hiring managers look for:
1. **Architectural Causality:** *Why* an engineering tool was selected and *how* bottlenecks were mitigated.
2. **Quantifiable Scope:** Measurable business and technical outcomes (Google XYZ format: *Accomplished [X], measured by [Y], by doing [Z]*).
3. **Engineering Depth:** Distinguishing between surface-level library consumers and engineers who understand concurrency, write contention, and distributed failure modes.

**Bar-Raiser** operationalizes this hiring rubric using strict structured validation via Pydantic and low-latency evaluation pipelines.

---

## 🛠️ Architecture & Tech Stack

┌──────────────┐       multipart/form-data
│   Frontend   │ ─────────────────────────────┐
│ (Vanilla JS, │                              ▼
│ Glassmorphic │                      ┌──────────────┐
│  Dashboard)  │ ◄────────────────────│ FastAPI App  │
└──────────────┘       JSON Schema    └──────┬───────┘
│
Extract AST    ▼
┌──────────────┐
│ PDF Ingestion│
│  (pypdf AST) │
└──────┬───────┘
│
Normalized Extraction ▼
┌──────────────┐
│  Gemini Flash│
│    Engine    │
└──────┬───────┘
│
Pydantic Type Contract ▼
┌──────────────┐
│ ResumeAudit  │
│ Report Model │
└──────────────┘


* **Backend Framework:** FastAPI (Asynchronous request lifecycle, non-blocking I/O).
* **Ingestion Layer:** Custom PDF layout-aware AST bullet extraction pipeline.
* **LLM Engine:** Google Gemini Flash via structured JSON schema enforcement.
* **Type Safety & Data Contracts:** Pydantic v2 enforcing strict typing, enum validation (`VERIFIED` | `SURFACE` | `MISSING`), and boundary constraints on numeric KPIs.
* **Frontend:** Zero-framework, lightweight CSS Grid/Flexbox UI with custom SVG visual cues, live tab filtering, and instant LaTeX/Markdown clipboard transforms.

---

## ✨ Key Capabilities

### 1. 4-Dimension Metric Dashboard
* **Assessed Seniority:** Classifies practical execution scope (`Intern`, `Junior`, `Mid-Level`, `Senior`, `Staff`).
* **JD Alignment Fit:** Quantifies semantic alignment between candidate experience and role demands.
* **Google XYZ Adherence:** Computes the exact percentage of bullets featuring verified metrics, actions, and quantifiable outcomes.
* **Zero-Proof Audit:** Identifies declared competencies that lack accompanying implementation details.

### 2. Live-Filtered Skill & Architecture Matrix
* Audits core competencies into tri-state confidence levels:
  * `VERIFIED`: Proven hands-on implementation with architectural context.
  * `SURFACE`: Mentioned casually or listed purely in a skills list without operational detail.
  * `MISSING`: Critical requirements absent from the profile.
* Categorizes technologies by domain (e.g., *Databases & Caching*, *Distributed Systems*, *Core Backend*).

### 3. Git-Diff Action Bullet Refactoring
* Visual split diff (`- Original` / `+ Rewrite`) showing precise structural fixes.
* Diagnostic categorization tags: `Missing Metric`, `Vague Scope`, `Passive Implementation`.
* Instant 1-click export to plain text or compiled LaTeX (`\item ...`).

### 4. Hiring Manager Interrogation Deck
* Generates role-specific systems architecture questions targeting potential edge cases, write scalability, thread safety, and latency trade-offs identified in the candidate's actual projects.

---

## 📊 Output Data Contract

The engine enforces runtime schema validation across four key payloads:

| Payload Node | Description | Verification Constraint |
| :--- | :--- | :--- |
| `candidate_level_assessed` | Assessed practical seniority | Seniority enum mapping |
| `skill_matrix` | Verified competency breakdown | `VERIFIED` \| `SURFACE` \| `MISSING` |
| `bullet_audits` | Split Git-diff bullet rewrites | 1–10 technical coherence score |
| `hiring_manager_interrogations` | Architectural drill questions | Edge-case & concurrency probing |

---

## 🚀 Quickstart & Setup

### Prerequisites
* Python 3.10+
* Google Gemini API Key

### 1. Clone & Configure Environment
```bash
git clone [https://github.com/](https://github.com/)<YOUR_USERNAME>/resume-bar-raiser-audit.git
cd resume-bar-raiser-audit

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
2. Configure Environment Variables
Create a .env file in the project root:

Code snippet
GEMINI_API_KEY="your-gemini-api-key-here"
3. Start the Server
Bash
uvicorn main:app --reload
Navigate to http://127.0.0.1:8000 to access the dashboard.

🛡️ Design Decisions & Trade-Offs
Strict Structured Outputs over Raw LLM Text: LLM outputs are directly bound to typed Pydantic models with constrained enums to prevent hallucinated keys and protect the frontend UI from rendering crashes.

Low-Overhead Vanilla Frontend: Zero heavy JavaScript framework dependencies (no React/Vue bundle overhead), ensuring near-instant hydration, local execution, and straightforward single-asset deployments.

Sanitization at Ingestion & Ingress: Project header cleaning strips stray OCR tags and dates, preventing dirty LLM parsing and keeping generated Git diffs clean and readable.