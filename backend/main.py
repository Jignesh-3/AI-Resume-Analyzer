import os
import json
import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.schemas import ResumeAuditReport, StatsResponse
from backend.parser import extract_resume_data
from backend.analyzer import audit_resume_with_llm
from backend.pdf_generator import generate_ats_pdf

load_dotenv()

# --------------------------------------------------
# Structured Production Logging
# --------------------------------------------------
logger = logging.getLogger("bar_raiser.api")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

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

# --------------------------------------------------
# Firebase / Firestore Setup
# --------------------------------------------------
db = None
STATS_COLLECTION = "analytics"
STATS_DOC = "site_stats"
STATS_FILE = Path("audit_stats.txt")

try:
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    key_file = Path("serviceAccountKey.json")

    if cred_json:
        # Render Production: read raw JSON credentials from environment
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firestore initialized via FIREBASE_CREDENTIALS_JSON env var.")
    elif key_file.exists():
        # Local Development: read local key file
        cred = credentials.Certificate(str(key_file))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firestore initialized via serviceAccountKey.json.")
    else:
        logger.warning("No Firebase credentials located. Falling back to local file counter.")
except Exception as e:
    logger.warning("Firebase initialization error: %s. Falling back to file storage.", e)


def get_audit_count() -> int:
    """Reads current audit count from Firestore, falling back to local file/baseline."""
    if db:
        try:
            doc_ref = db.collection(STATS_COLLECTION).document(STATS_DOC)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict() or {}
                return data.get("total_audits", 40)
            else:
                # Seed document starting at initial verified baseline
                doc_ref.set({"total_audits": 40})
                return 32
        except Exception as e:
            logger.error("Firestore read error: %s", e)

    if not STATS_FILE.exists():
        return 40
    try:
        return int(STATS_FILE.read_text().strip())
    except Exception:
        return 40


def increment_audit_count():
    """Atomically increments audit counter in Firestore (or local file) as a background task."""
    if db:
        try:
            doc_ref = db.collection(STATS_COLLECTION).document(STATS_DOC)
            doc_ref.set(
                {"total_audits": firestore.Increment(1)},
                merge=True
            )
            return
        except Exception as e:
            logger.error("Firestore increment error: %s", e)

    try:
        count = get_audit_count() + 1
        STATS_FILE.write_text(str(count))
    except Exception as e:
        logger.error("Local file counter increment error: %s", e)


# --------------------------------------------------
# API Routes
# --------------------------------------------------
@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Returns the total number of audits completed."""
    return StatsResponse(total_audits=get_audit_count())


@app.post("/api/analyze", response_model=ResumeAuditReport)
async def analyze_resume(
    background_tasks: BackgroundTasks,
    resume_file: UploadFile = File(...),
    job_description: Optional[str] = Form(default=""),
    preset_key: Optional[str] = Form(default="backend_python")
):
    """
    Ingests resume PDF and evaluates against JD or Preset Rubric.
    Uses threadpools, background task dispatch, and telemetry logging.
    """
    total_start = time.time()
    if not resume_file.filename or not resume_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file. Only PDF resumes are accepted.")

    try:
        read_start = time.time()
        pdf_bytes = await resume_file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")
        logger.info("Stage [1/4] File read completed in %.3fs", time.time() - read_start)

        # 1. Parse PDF off main event loop (CPU-bound)
        parse_start = time.time()
        full_text, bullets = await run_in_threadpool(extract_resume_data, pdf_bytes)
        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract readable text from PDF. Ensure it is not a scanned image."
            )
        logger.info(
            "Stage [2/4] PDF Parse & AST Extraction completed in %.3fs (%d bullets)",
            time.time() - parse_start,
            len(bullets)
        )

        # 2. Run Bar-Raiser LLM Audit off main event loop (I/O & Network bound)
        llm_start = time.time()
        report = await run_in_threadpool(
            audit_resume_with_llm,
            resume_text=full_text,
            bullets=bullets,
            job_description=job_description or "",
            preset_key=preset_key or "backend_python"
        )
        logger.info("Stage [3/4] LLM Inference & Schema Validation completed in %.3fs", time.time() - llm_start)

        # 3. Non-blocking Firestore counter dispatched post-response
        background_tasks.add_task(increment_audit_count)
        logger.info("Stage [4/4] Firestore counter increment dispatched to background tasks")

        logger.info("Pipeline Complete - Total Response Duration: %.3fs", time.time() - total_start)
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unhandled exception in /api/analyze: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# ATS PDF Export Endpoint
# --------------------------------------------------
class ResumeExportRequest(BaseModel):
    candidate_name: Optional[str] = "Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    experiences: Optional[List[Dict[str, Any]]] = []
    skills: Optional[Dict[str, Any]] = {}
    education: Optional[List[Dict[str, Any]]] = []


@app.post("/api/export-ats-pdf")
async def export_ats_pdf(payload: ResumeExportRequest):
    """
    Generates and streams an ATS-optimized, machine-readable PDF on the fly.
    """
    data = payload.model_dump()
    pdf_buffer = await run_in_threadpool(generate_ats_pdf, data)
    
    clean_name = (payload.candidate_name or "Candidate").replace(" ", "_")
    filename = f"{clean_name}_ATS_Optimized.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# --------------------------------------------------
# Mount Static Frontend
# --------------------------------------------------
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