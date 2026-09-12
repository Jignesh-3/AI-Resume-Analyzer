import os
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.schemas import ResumeAuditReport, StatsResponse
from backend.parser import extract_resume_data
from backend.analyzer import audit_resume_with_llm

load_dotenv()

app = FastAPI(
    title="Proof-of-Work Resume Analyzer",
    description="Bar-Raiser Technical Audit & Causality Engine",
    version="3.0.0"
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory / file counter fallback
STATS_FILE = Path("audit_stats.txt")

def get_audit_count() -> int:
    if not STATS_FILE.exists():
        return 18  # Matches recent run baseline
    try:
        return int(STATS_FILE.read_text().strip())
    except Exception:
        return 18

def increment_audit_count() -> int:
    count = get_audit_count() + 1
    try:
        STATS_FILE.write_text(str(count))
    except Exception:
        pass
    return count


# --------------------------------------------------
# API Routes
# --------------------------------------------------
@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Returns the total number of audits completed."""
    return StatsResponse(total_audits=get_audit_count())


@app.post("/api/analyze", response_model=ResumeAuditReport)
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description: Optional[str] = Form(default=""),
    preset_key: Optional[str] = Form(default="backend_python")
):
    """
    Ingests resume PDF and evaluates against JD or Preset Rubric.
    Explicit defaults prevent 422 Unprocessable Content errors.
    """
    if not resume_file.filename or not resume_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file. Only PDF resumes are accepted.")

    try:
        pdf_bytes = await resume_file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

        # 1. Parse PDF and extract AST bullet nodes
        full_text, bullets = extract_resume_data(pdf_bytes)
        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract readable text from PDF. Ensure it is not a scanned image."
            )

        # 2. Run Bar-Raiser LLM Audit with Gemini
        report = audit_resume_with_llm(
            resume_text=full_text,
            bullets=bullets,
            job_description=job_description or "",
            preset_key=preset_key or "backend_python"
        )

        # 3. Track analytics
        increment_audit_count()

        return report

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR /api/analyze]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# Mount Static Frontend
# --------------------------------------------------
# Resolves frontend folder whether launched from root or backend/
BASE_DIR = Path(__file__).resolve().parent.parent
frontend_path = BASE_DIR / "frontend"
if not frontend_path.exists():
    frontend_path = Path(__file__).resolve().parent / "frontend"

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(str(frontend_path / "styles.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(frontend_path / "app.js"), media_type="application/javascript")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)