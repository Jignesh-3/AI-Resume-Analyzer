from typing import List, Optional
from pydantic import BaseModel, Field


class SkillMatrixItem(BaseModel):
    skill: str = Field(..., description="Name of the technology or engineering concept")
    domain_category: str = Field(..., description="Category (e.g., Core Backend, Databases & Caching, Cloud & DevOps)")
    importance: str = Field("PREFERRED", description="CRITICAL or PREFERRED")
    status: str = Field("VERIFIED", description="VERIFIED, SURFACE, or MISSING")
    evidence: str = Field(..., description="Causality analysis or rationale for the status assigned")


class BulletAuditItem(BaseModel):
    original_text: str = Field(..., description="Original raw bullet point from the resume")
    critique: str = Field(..., description="Actionable bar-raiser critique identifying missing causality or metrics")
    suggested_diff_rewrite: str = Field(..., description="Google XYZ standard rewrite: Accomplished [X] as measured by [Y], by doing [Z]")
    has_measurable_metric: bool = Field(False, description="True if a quantifiable metric is present in original text")
    detected_metric: Optional[str] = Field(None, description="The specific quantitative metric found, if any")
    technical_coherence_score: int = Field(..., ge=1, le=10, description="Coherence and engineering depth rating out of 10")
    possible_interview_questions: List[str] = Field(
        default_factory=list,
        description="Technical probing questions a hiring manager would ask based on this claim"
    )
    winning_response_formula: Optional[str] = Field(
        None,
        description="What architectural trade-offs, metrics, or mechanisms the candidate must mention to pass"
    )


class ResumeAuditReport(BaseModel):
    candidate_level_assessed: str = Field(..., description="Assessed engineering level (e.g., Junior, Mid-Level, Senior Backend Engineer)")
    target_match_percentage: int = Field(..., ge=0, le=100, description="Match percentage against target JD requirements (0 to 100)")
    technical_fit_summary: str = Field(..., description="2-3 sentence executive assessment of engineering depth and system fit")
    overclaimed_buzzwords: List[str] = Field(
        default_factory=list,
        description="Technologies listed in skills sections that have zero implementation proof across projects"
    )
    skill_matrix: List[SkillMatrixItem] = Field(
        default_factory=list,
        description="Granular skill alignment and verification matrix"
    )
    bullet_audits: List[BulletAuditItem] = Field(
        default_factory=list,
        description="In-depth audit of project and experience bullet points"
    )


class StatsResponse(BaseModel):
    total_audits: int