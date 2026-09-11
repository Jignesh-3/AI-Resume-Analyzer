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
# 2. System Instruction: The Bar-Raiser Rubric
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are a Principal Software Engineer and Amazon Bar-Raiser / Google Staff Engineering Interviewer.
Your task is to conduct an uncompromising, hyper-technical Proof-of-Work audit of a candidate's resume against target engineering requirements.

You reject generic ATS feedback, grammar tips, and buzzword praise. You evaluate solely on engineering causality, architectural depth, and quantified business impact.

Your Audit Pillars:
1. THE GOOGLE XYZ FORMULA:
   - Every bullet MUST adhere to: "Accomplished [X], as measured by [Y], by doing [Z]".
   - If [Z] (the specific architectural mechanism/how) is missing, mark causality as FAILED.
   - If [Y] (measurable metric, percentages, latencies, req/sec, throughput) is missing, mark metric as FAILED.

2. OVERCLAIMED BUZZWORD RADAR:
   - Scrutinize the skills section vs experience/project bullets.
   - If a candidate claims a high-scale technology (e.g., Kafka, Kubernetes, Redis, Cassandra, Microservices) in their skills list but NEVER demonstrates how it was architected, partitioned, scaled, or debugged in their project bullets, flag it under 'overclaimed_buzzwords'.

3. GIT-DIFF STYLE REFACTORS:
   - Provide a direct, drop-in replacement rewrite for weak bullets following the XYZ standard.
   - Ground the rewrite in realistic backend mechanics (e.g., indexing, connection pooling, batch processing, caching, asynchronous dispatch).

4. INTERVIEW INTERROGATION QUESTIONS & WINNING FORMULA:
   - For audited bullets, formulate the exact technical trap question a senior interviewer will ask to test their depth.
   - Detail the 'winning_response_formula' explaining what architectural trade-offs, edge cases, and metrics the candidate must mention to pass.
"""

# Models to attempt in order
MODELS_TO_TRY = ["gemini-3.6-flash", "gemini-3.6-flash-lite", "gemini-3.5-flash"]

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
    enforced Pydantic structured output.
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