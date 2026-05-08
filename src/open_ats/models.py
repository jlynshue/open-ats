"""Pydantic v2 entity definitions for open-ats.

This module is the canonical implementation of the data model documented
in ``docs/PRD.md`` §7. Field names, types, and validators MUST match the
PRD; amendments require a paired update to that section.

The module is import-time cheap (only stdlib + pydantic + typing). No
business logic lives here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl

# ─── Enums ────────────────────────────────────────────────────────────


class SectionType(str, Enum):
    """Canonical resume section taxonomy."""

    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    PUBLICATIONS = "publications"
    AWARDS = "awards"
    OTHER = "other"


class KeywordCategory(str, Enum):
    """How a matched keyword contributes to scoring."""

    HARD_SKILL = "hard_skill"
    SOFT_SKILL = "soft_skill"
    ACTION_VERB = "action_verb"
    INDUSTRY_TERM = "industry_term"


class Rating(str, Enum):
    """Score rating buckets per PRD §8."""

    EXCELLENT = "excellent"  # 80-100
    GOOD = "good"  # 70-79
    FAIR = "fair"  # 60-69
    POOR = "poor"  # 0-59


RoleLevel = Literal["entry", "mid", "senior", "executive"]
SourceFormat = Literal["markdown", "docx", "pdf", "txt"]
Severity = Literal["info", "warning", "error"]


# ─── Resume entities ───────────────────────────────────────────────────


class Contact(BaseModel):
    """Contact details extracted from the header region of a resume."""

    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: HttpUrl | None = None
    github: HttpUrl | None = None
    website: HttpUrl | None = None


class ExperienceEntry(BaseModel):
    """One position / role under the Experience section."""

    title: str
    company: str
    location: str | None = None
    # Dates accept loose formats: "2023-03", "March 2023", "2023", "Present".
    # Strict parsing into datetime is deferred until needed.
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """One degree under the Education section."""

    degree: str
    institution: str
    location: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    gpa: float | None = None
    coursework: list[str] = Field(default_factory=list)


class Section(BaseModel):
    """A detected section in a resume.

    ``raw_heading`` preserves the literal source text so reporters can
    show the user how their headings were interpreted.
    """

    type: SectionType
    raw_heading: str
    body: str
    bullets: list[str] = Field(default_factory=list)


class ParserWarning(BaseModel):
    """Non-fatal anomaly detected during parsing.

    Codes follow a dotted convention: ``<area>.<specific_issue>``. See
    ``docs/PRD.md`` §0 amendments for the canonical list as it grows.
    """

    code: str
    message: str
    severity: Severity = "warning"


class Resume(BaseModel):
    """A parsed resume — the central input to the analyzer pipeline."""

    source_path: Path | None = None
    source_format: SourceFormat
    contact: Contact
    summary: str | None = None
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    word_count: int = 0
    parser_warnings: list[ParserWarning] = Field(default_factory=list)


# ─── Job description ──────────────────────────────────────────────────


class JobDescription(BaseModel):
    """A parsed job description."""

    source_path: Path | None = None
    title: str | None = None
    company: str | None = None
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    keywords: list[Keyword] = Field(default_factory=list)
    raw_text: str = ""
    parser_warnings: list[ParserWarning] = Field(default_factory=list)


# ─── Keyword matching ──────────────────────────────────────────────────


class Keyword(BaseModel):
    """A keyword tracked during matching."""

    canonical: str
    category: KeywordCategory
    synonyms: list[str] = Field(default_factory=list)
    matched: bool = False
    match_count: int = 0


# Forward-ref resolution for JobDescription.keywords:
JobDescription.model_rebuild()


# ─── Analyzer outputs ──────────────────────────────────────────────────


class AnalyzerResult(BaseModel):
    """One analyzer's contribution to the overall scan."""

    analyzer: str
    score: float = Field(ge=0.0, le=100.0)
    sub_scores: dict[str, float] = Field(default_factory=dict)
    matched_items: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Scoring ──────────────────────────────────────────────────────────


class ScoringConfig(BaseModel):
    """Per-scan configuration for the scoring engine."""

    role_level: RoleLevel = "mid"
    weights: dict[str, float]
    industry: str | None = None
    custom_keyword_db: Path | None = None


class CategoryScore(BaseModel):
    """One top-level scoring category (keyword, quantification, ...)."""

    name: str
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0)
    contribution: float
    sub_scores: dict[str, float] = Field(default_factory=dict)


class FormulaAuditEntry(BaseModel):
    """One step in the score-construction audit trail.

    Every numerical step that produced the final score MUST appear here
    so reports can show the formula end-to-end (transparency contract,
    NFR-1).
    """

    step: str
    formula: str
    inputs: dict[str, float]
    output: float


class Recommendation(BaseModel):
    """An actionable improvement suggestion."""

    category: str
    severity: Literal["info", "low", "medium", "high"]
    message: str
    expected_score_impact: float = Field(ge=0.0, le=100.0)
    related_items: list[str] = Field(default_factory=list)


class Score(BaseModel):
    """The full score for one scan."""

    overall: float = Field(ge=0.0, le=100.0)
    rating: Rating
    categories: list[CategoryScore]
    formula_audit: list[FormulaAuditEntry]
    recommendations: list[Recommendation] = Field(default_factory=list)


# ─── Scan result ──────────────────────────────────────────────────────


class ScanResult(BaseModel):
    """The complete output of one scan — what gets persisted and reported."""

    scan_id: str
    timestamp: datetime
    open_ats_version: str
    resume_hash: str
    jd_hash: str
    resume: Resume
    job_description: JobDescription
    analyzer_results: list[AnalyzerResult]
    score: Score
    config: ScoringConfig


# ─── Audit trail ──────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    """Index row in the SQLite audit DB; full ScanResult stored as JSON."""

    scan_id: str
    timestamp: datetime
    resume_path: Path
    jd_path: Path
    resume_hash: str
    jd_hash: str
    score_overall: float
    score_rating: Rating
    role_level: RoleLevel
    open_ats_version: str


__all__ = [
    "AnalyzerResult",
    "AuditEntry",
    "CategoryScore",
    "Contact",
    "EducationEntry",
    "ExperienceEntry",
    "FormulaAuditEntry",
    "JobDescription",
    "Keyword",
    "KeywordCategory",
    "ParserWarning",
    "Rating",
    "Recommendation",
    "Resume",
    "RoleLevel",
    "ScanResult",
    "Score",
    "ScoringConfig",
    "Section",
    "SectionType",
    "Severity",
    "SourceFormat",
]
