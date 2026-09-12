import json
import os
import time
from typing import Dict, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.schemas import ResumeAuditReport

# ---------------------------------------------------------------------------
# 1. Target Role Presets (Zero-Friction Audits without pasting a JD)
# ---------------------------------------------------------------------------
ROLE_PRESETS: Dict[str, str] = {
    "backend_python": """
    Target Role: Backend Software Engineer (Python / High Concurrency)
    Core Expectations:
    - Deep knowledge of asynchronous programming (FastAPI, asyncio, ASGI).
    - Relational data modeling & SQL query optimization (PostgreSQL, connection pooling, indexing, execution plans).
    - Caching strategies and invalidation patterns (Redis, LRU/LFU, TTL policies).
    - Distributed systems fundamentals: message queues (Kafka, RabbitMQ), idempotency, horizontal scalability.
    - System reliability: p95/p99 latency optimization, rate limiting, and observability.
    """,
    
    "backend_general": """
    Target Role: Core Backend Platform Engineer
    Core Expectations:
    - Microservices or modular monolith architecture with clean domain-driven boundaries.
    - Strong database indexing, ACID compliance, transaction isolation levels, and migration strategies.
    - RESTful and gRPC API contract design with schema validation.
    - Concurrency control, thread safety, rate-limiting, and fault-tolerance patterns (circuit breakers, retries with jitter).
    - CI/CD container workflows with Docker and Linux system performance basics.
    """,
    
    "distributed_systems": """
    Target Role: Distributed Systems & Infrastructure Engineer
    Core Expectations:
    - Event-driven pipelines, event-sourcing, Kafka/Pulsar partition topologies, consumer lag tuning.
    - Consensus protocols, distributed transactions (Saga, 2PC), and eventual consistency patterns.
    - High-throughput ingestion pipelines, dead-letter queue (DLQ) replay, and backpressure mechanisms.
    - Chaos engineering, observability (OpenTelemetry, Prometheus, distributed tracing), and fault domain isolation.
    """,
    
    "fullstack_product": """
    Target Role: Full-Stack Product Engineer (Backend Lean)
    Core Expectations:
    - End-to-end feature delivery: robust backend APIs paired with responsive client state management.
    - Database query optimization, secure authentication (OAuth2, JWT, RBAC), and third-party webhook integrations.
    - Core Web Vitals, API latency reduction, caching, and database transaction safety.
    - Automated testing (unit, integration, and contract tests) and pragmatic technical trade-off decisions.
    """
}

# ---------------------------------------------------------------------------
# 2. System Instruction: The Bar-Raiser Rubric (Clip 2 Standard)
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are a Principal Software Engineer and Amazon Bar-Raiser / Google Staff Systems Interviewer.
Your task is to conduct an uncompromising, hyper-technical Proof-of-Work audit of a candidate's resume against target engineering benchmarks.

You reject generic ATS buzzwords, grammar tips, and empty praise. You evaluate strictly on engineering causality, architectural depth, and quantified business impact.

Your Core Audit Directives:

1. TOP-LEVEL KPI METRICS:
   - 'candidate_level_assessed': Concise level assessment (e.g., 'Junior', 'Mid-Level', 'Senior').
   - 'seniority_subtext': Brief subtext indicator (e.g., 'Engineering Depth', 'System Scope').
   - 'target_match_percentage': 0 to 100 percentage reflecting proof-backed alignment against the target role requirements.
   - 'xyz_adherence_percentage': Explicit calculation (0 to 100) of bullet points strictly adhering to Google's XYZ formula: "Accomplished [X], as measured by [Y], by doing [Z]".
   - 'unbacked_skills_count': The exact count of technologies claimed in the skills list with zero project evidence.

2. SKILL GAP & ARCHITECTURE MATRIX:
   - Identify 5 to 7 key competencies relevant to the target role.
   - For each skill, status MUST be strictly one of: 'VERIFIED', 'SURFACE', or 'MISSING' (UPPERCASE).
   - VERIFIED: The skill is demonstrated in a project with clear usage context, architectural intent, or practical implementation (e.g., built endpoints using FastAPI, created schemas in PostgreSQL, or trained/inferred a model). It does NOT require FAANG-scale production metrics to be verified.
   - SURFACE: The technology is mentioned in passing or listed in a project stack without explaining what role it played or how it was integrated.
   - MISSING: The skill is either listed only in the skills list with no project mention, or completely absent from the resume despite being a role requirement.

3. BULLET AUDIT & GIT-DIFF REFACTORS:
   - 'project_context': Clean project/company title ONLY. Strip any OCR artifacts, IDs, or timestamps (e.g., convert "61970376 Smart Surveillance" -> "Smart Surveillance System").
   - 'diagnostic_tag': Concise diagnostic badge (e.g., 'Missing Metric', 'Vague Scope', 'Weak Causality', 'Passive Action').
   - 'technical_coherence_score': Objective score from 1 to 10.
   - 'critique': Bar-Raiser critique pinpointing technical ambiguity and missing metrics.
   - 'suggested_diff_rewrite': High-impact, drop-in replacement following Google XYZ with realistic metrics (p95 latency, RPS, memory reduction, concurrency).

4. HIRING MANAGER CLAIM INTERROGATION:
   - In 'hiring_manager_interrogations', formulate 5 to 7 razor-sharp systems-design questions attacking potential failure modes, thread safety, indexing bottlenecks, and unproven claims.
"""

# Models to attempt in order
MODELS_TO_TRY = ["gemini-3.7-flash", "gemini-3.6-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash"]

# ---------------------------------------------------------------------------
# 3. Main Audit Execution Function
# ---------------------------------------------------------------------------
def audit_resume_with_llm(
    resume_text: str,
    bullets: List[str],
    job_description: Optional[str] = None,
    preset_key: Optional[str] = None,
    api_key: Optional[str] = None
) -> ResumeAuditReport:
    """
    Submits extracted resume data and JD/preset criteria to Gemini with strictly
    enforced Pydantic structured output matching the Clip 2 dashboard schema.
    """
    client_api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not client_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    client = genai.Client(api_key=client_api_key)

    # Determine target criteria: custom JD, preset, or default backend rubric
    if job_description and job_description.strip():
        target_criteria = f"Target Job Description:\n{job_description.strip()}"
    elif preset_key and preset_key in ROLE_PRESETS:
        target_criteria = f"Target Role Preset Rubric:\n{ROLE_PRESETS[preset_key]}"
    else:
        target_criteria = f"Default Target Role Rubric:\n{ROLE_PRESETS['backend_python']}"

    bullets_formatted = "\n".join([f"- {b}" for b in bullets]) if bullets else "No isolated bullets found; evaluate resume text directly."

    prompt = f"""
    {target_criteria}

    === CANDIDATE RESUME FULL TEXT ===
    {resume_text}

    === CANDIDATE EXTRACTED BULLET POINTS (AST NODES) ===
    {bullets_formatted}

    Perform the Bar-Raiser technical audit. Return your evaluation strictly adhering to the specified schema.
    """

    last_error = None

    # Loop through models with backoff retry
    for model_name in MODELS_TO_TRY:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=ResumeAuditReport,
                        temperature=0.1,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                if response.text:
                    return ResumeAuditReport.model_validate_json(response.text)
            except APIError as e:
                last_error = e
                # Retry on 503 (high demand) or 429 (rate limit)
                if getattr(e, "code", None) in [503, 429]:
                    time.sleep(1)
                    continue
                break
            except Exception as e:
                last_error = e
                break

    raise RuntimeError(f"Audit analysis failed across models: {last_error}")