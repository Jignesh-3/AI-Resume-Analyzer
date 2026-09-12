from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SkillMatrixItem(BaseModel):
    skill: str = Field(..., description="Name of the technology or engineering concept")
    domain_category: str = Field(..., description="Category (e.g., Core Backend, Databases & Caching, Architecture & Systems, Cloud & DevOps)")
    importance: Literal["CRITICAL", "PREFERRED"] = Field("PREFERRED", description="Importance for target role")
    status: Literal["VERIFIED", "SURFACE", "MISSING"] = Field("VERIFIED", description="Verification level")
    evidence: str = Field(..., description="Causality analysis or rationale for the status assigned")


class BulletAuditItem(BaseModel):
    project_context: str = Field(..., description="Clean name of the project or company (e.g., 'Smart Surveillance System') without IDs or raw artifacts")
    diagnostic_tag: str = Field(..., description="Short badge label like 'Missing Metric', 'Vague Scope', 'Weak Causality', or 'Passive Action'")
    original_text: str = Field(..., description="Original raw bullet point from the resume")
    critique: str = Field(..., description="Actionable bar-raiser critique explaining why this claim fails technical scrutiny")
    suggested_diff_rewrite: str = Field(..., description="Google XYZ standard rewrite: Accomplished [X] as measured by [Y], by doing [Z]")
    technical_coherence_score: int = Field(..., ge=1, le=10, description="Coherence and engineering depth rating out of 10")
    has_measurable_metric: bool = Field(False, description="True if a quantifiable metric is present in original text")
    detected_metric: Optional[str] = Field(None, description="The specific quantitative metric found, if any")
    possible_interview_questions: List[str] = Field(
        default_factory=list,
        description="Specific technical probing questions a hiring manager would ask based on this claim"
    )
    winning_response_formula: Optional[str] = Field(
        None,
        description="Architectural trade-offs, metrics, or mechanisms the candidate must mention to pass"
    )


class ResumeAuditReport(BaseModel):
    # Top 4 KPI Metrics
    candidate_level_assessed: str = Field(..., description="Assessed level (e.g., 'Junior', 'Mid-Level', 'Senior')")
    seniority_subtext: str = Field("Engineering Depth", description="Subtext badge under seniority")
    target_match_percentage: int = Field(..., ge=0, le=100, description="Proof-backed match against target requirements (0 to 100)")
    xyz_adherence_percentage: int = Field(..., ge=0, le=100, description="Percentage of bullets adhering to Google XYZ formula")
    unbacked_skills_count: int = Field(..., description="Count of overclaimed skills with zero implementation proof")
    
    # Executive & Skills Breakdown
    overclaimed_buzzwords: List[str] = Field(
        default_factory=list,
        description="Technologies listed in skills sections that have zero implementation proof across projects"
    )
    technical_fit_summary: str = Field(..., description="Executive technical assessment highlighting foundational strengths and engineering scope gaps")
    skill_matrix: List[SkillMatrixItem] = Field(
        default_factory=list,
        description="Granular skill alignment and verification matrix"
    )
    
    # Refactors & Top-Level Interrogations
    bullet_audits: List[BulletAuditItem] = Field(
        default_factory=list,
        description="In-depth audit and git-diff refactors of project/experience bullet points"
    )
    hiring_manager_interrogations: List[str] = Field(
        default_factory=list,
        description="5 to 7 high-friction architectural interrogation questions probing concurrency, failure modes, and depth"
    )


class StatsResponse(BaseModel):
    total_audits: int