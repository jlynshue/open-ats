# Product Requirements Document — Open ATS Resume Scanner

**Version:** 1.0
**Date:** 2026-05-08
**Status:** Sprint 0 — Authoritative source of truth for Sprints 1–13.

---

## 0. How This Document Is Used

This PRD is the **execution contract** for the open-ats engineering effort. Each functional requirement (FR-N) is paired with **Given / When / Then** acceptance criteria that map directly to test cases. Each entity is defined as a Pydantic v2 model; implementations MUST match the field names, types, and validators specified here.

Sprints land features against these criteria. Amendments to this PRD require a `docs:` PR with a clear rationale.

---

## 1. Executive Summary

Open ATS is an open-source resume scanner that emulates commercial ATS-checkers (JobScan, Resume Worded) while making every scoring decision **auditable**, **deterministic**, and **unlimited**. The scanner is delivered as a Python package and CLI; a web UI is planned for Phase 2.

**Differentiators:**

| Concern | Commercial tools | Open ATS |
|---|---|---|
| Scoring formulas | Black-box | Visible in every report (`formula_audit` field) |
| Scan limit | 5/month free | Unlimited |
| Audit trail | Limited | Complete (SQLite-backed history) |
| Customization | Fixed | Configurable weights per role level |
| Cost | $50–90/mo | Free, MIT-licensed |

**Validation north star:** ≥0.90 Pearson correlation against JobScan on a 100-pair holdout (gated to v1.0 / Sprint 13). MVP through v0.4.0 validates via internal consistency + golden cases.

---

## 2. Goals & Success Metrics

### Product goals
1. Match commercial tool scoring within 90% correlation on hard-skill-heavy job categories
2. Surface every formula in user-facing reports
3. Enable unlimited iteration without artificial scan caps
4. Provide complete history so users can prove improvement over time

### Engineering goals (per `tests/validation/`)
- Determinism: identical input → bit-identical output (gate from Sprint 11)
- Performance: end-to-end scan <5 sec on a 2-page resume + 1-page JD (NFR-1)
- Coverage: ≥80% line coverage repo-wide; ≥85% on scoring + analyzers
- Type safety: `mypy --strict` clean on `src/`

### KPIs (post-launch)
- p50 scan time
- Reports-per-week
- JobScan correlation (test corpus vs production sample if any)

---

## 3. Scope

### In scope (MVP, v0.2 → v0.4)
- Resume parsing: Markdown, DOCX, PDF, TXT
- JD parsing: plain-text and Markdown
- Analyzers: keyword, quantification, formatting, content quality
- Transparent scoring with configurable role-level presets
- Reports: JSON + HTML (PDF deferred to v1.1)
- Audit trail: SQLite store, compare, batch
- CLI: `scan`, `batch`, `compare`

### Out of scope (deferred)
- Web UI / FastAPI server (v1.2)
- Multi-language (post-v1.0)
- ATS vendor-specific profiles (Taleo, Workday, Greenhouse — v2.0)
- ML-based scoring optimization (v2.0)
- Cover letter analysis (v2.0)
- LinkedIn profile optimization (v2.0)

---

## 4. User Personas

| Persona | Use case | What they value |
|---|---|---|
| **Active job seeker** | Iterating on a resume against multiple JDs | Speed, clarity, unlimited scans |
| **Career coach** | Producing reports for clients | Reproducibility, professional output |
| **Recruiter / sourcing operator** | Bulk evaluation | Batch CLI, deterministic ranking |
| **Career-services office (university)** | Self-hosted tool for students | Free, local, no PII leaving disk |
| **OSS contributor** | Adding industry keyword lists | Clear schemas, tests as docs |

---

## 5. Functional Requirements

### FR-1 — Resume parsing

The scanner MUST parse resumes in Markdown, DOCX, PDF, and plain text into a `Resume` entity (§9) with ≥90% accuracy on contact-section fields.

**FR-1.1 — Markdown parser** (Sprint 1)
- *Given* a well-formed Markdown resume, *when* `parse_resume(path)` is called, *then* it returns a `Resume` with `contact.email` and `contact.full_name` populated and at least three of `Section.SUMMARY`, `Section.EXPERIENCE`, `Section.EDUCATION`, `Section.SKILLS` detected.
- *Given* a Markdown resume missing an explicit "Summary" heading, *when* parsing, *then* the parser does NOT raise; it returns the resume with `summary=None` and `parser_warnings` containing one entry naming the missing section.
- *Given* a malformed Markdown file (binary garbage), *when* parsing, *then* `ResumeParseError` is raised with `cause` describing the failure.

**FR-1.2 — DOCX parser** (Sprint 2)
- *Given* a `.docx` resume produced by Microsoft Word or Google Docs export, *when* parsing, *then* contact details and ≥3 sections are extracted.
- *Given* a `.docx` containing tables for layout, *when* parsing, *then* the parser surfaces a `ParserWarning` of type `formatting.table_detected` but still returns a `Resume`.

**FR-1.3 — PDF parser** (Sprint 3)
- *Given* a single-column text-based PDF, *when* parsing, *then* contact details and ≥3 sections are extracted.
- *Given* a multi-column text-based PDF, *when* parsing, *then* extraction may degrade (≥2 sections) but does NOT raise.
- *Given* an image-based / scanned PDF (no extractable text), *when* parsing, *then* `ResumeParseError("PDF appears to be image-based; please convert to text-based PDF")` is raised.

**FR-1.4 — TXT parser** (Sprint 2)
- *Given* a plain-text resume with whitespace-separated sections, *when* parsing, *then* contact and ≥2 sections are extracted via heuristic section detection.

**FR-1.5 — Format dispatch** (Sprint 1)
- *Given* a path to an unsupported format, *when* `parse_resume(path)` is called, *then* `UnsupportedFormatError` is raised listing supported extensions.

### FR-2 — Job description parsing (Sprint 4)

- *Given* a plain-text JD, *when* `parse_job_description(path_or_str)` is called, *then* a `JobDescription` is returned with `requirements`, `responsibilities`, and `keywords` populated.
- *Given* a JD with a "Nice to have" or "Bonus" section, *when* parsing, *then* those items are tagged `JobDescription.preferences` rather than `requirements`.
- *Given* a JD shorter than 200 characters, *when* parsing, *then* `ParserWarning("jd.too_short")` is appended; the JD is still returned.

### FR-3 — Keyword matching (Sprint 5)

- *Given* a `Resume` and `JobDescription`, *when* `KeywordAnalyzer.analyze(resume, jd)` is called, *then* it returns `AnalyzerResult` with sub-scores for `hard_skills`, `soft_skills`, `action_verbs`, `industry_terms`.
- *Given* synonymous terms (e.g., "PostgreSQL" / "postgres"), *when* matching, *then* both are credited as a single hit.
- *Given* a JD requiring "Python" and a resume listing "Python", *when* matching, *then* the keyword is recorded with `Keyword.matched=True` and `Keyword.canonical="Python"`.

### FR-4 — Quantification analysis (Sprint 6)

- *Given* a resume bullet "Reduced infrastructure cost by 35% over six months", *when* analyzing, *then* the bullet is flagged as quantified and a `QuantificationMatch` is produced with `pattern="percentage"`.
- Target rates by role level: 60% of mid-level bullets quantified; 40% for executive (executives describe outcomes more abstractly); 50% for entry-level.
- Precision ≥85% and Recall ≥85% on annotated golden bullets (Sprint 6 deliverable).

### FR-5 — Formatting validation (Sprint 7)

- Penalty-based: starts at 100, subtract per issue.
- Detected issues and penalties:
  - Tables in resume body: −10
  - Date format inconsistency across roles: −5
  - Special non-ASCII characters that break ATS (em-dash, smart quotes used inconsistently): −1 per offense, capped at −10
  - Excessive line length (>120 chars): −3
  - Missing contact info: −15

### FR-6 — Content quality (Sprint 7)

Sub-scores:
- Action verb strength: 40%
- Passive voice absence: 30%
- Hedging language absence: 20%
- Word count fitness (target 400–800): 10%

### FR-7 — Transparent scoring engine (Sprint 8)

- *Given* analyzer outputs, *when* `ScoringEngine.score(results, config)` is called, *then* a `Score` is returned with `categories`, `subcategories`, `overall`, `rating`, and `formula_audit`.
- `formula_audit` MUST contain enough detail to reconstruct `overall` from sub-scores (transparency contract, NFR-1).
- Default weights:

  | Role level | Keyword | Quantification | Formatting | Content |
  |---|---|---|---|---|
  | entry | 35% | 25% | 20% | 20% |
  | mid (default) | 40% | 20% | 20% | 20% |
  | senior | 45% | 20% | 15% | 20% |
  | executive | 45% | 15% | 15% | 25% |

- Rating thresholds: Excellent 80–100, Good 70–79, Fair 60–69, Poor 0–59.

### FR-8 — Reports (Sprints 5, 9)

- JSON report (Sprint 5): canonical, deterministic, machine-readable; complete `formula_audit`.
- HTML report (Sprint 9): self-contained (no external CSS/JS), W3C-valid, <500KB typical, accessible (alt text, color contrast).
- PDF (deferred to v1.1).

### FR-9 — Audit trail (Sprint 10)

- SQLite-backed; default `~/.open-ats/audit.db`. Configurable via env or `--audit-db`.
- Each scan persists `AuditEntry` (§9) with full inputs hashed (SHA-256) and the complete `ScanResult`.
- `open-ats compare --from ID1 --to ID2` produces a delta report (HTML or JSON).

### FR-10 — CLI interface (Sprints 5, 10)

Command surface:
```
open-ats scan --resume R --job-description JD [--output OUT.{json|html}] [--config CFG.yaml] [--role-level entry|mid|senior|exec]
open-ats batch --resume-dir DIR --job-description JD --output-dir OUT
open-ats compare --from-scan ID --to-scan ID [--output OUT.{json|html}]
open-ats history [--limit N]
```

- `scan` exits 0 on success; non-zero with a stderr message on parse/analyzer failure.
- `--output` extension drives reporter selection: `.json` → JSON, `.html` → HTML.

---

## 6. Non-Functional Requirements

| ID | Requirement | Gate |
|---|---|---|
| NFR-1 | Performance: scan <5 sec, batch >10/min, mem <500MB per scan | Sprint 11 |
| NFR-2 | Scalability: batch handles 1000 resumes without OOM | Sprint 10 |
| NFR-3 | Reliability: zero data loss across audit-trail operations | Sprint 10 |
| NFR-4 | Security: input validation, no PII written to logs at default verbosity | All sprints; audited Sprint 12 |
| NFR-5 | Usability: every error includes actionable remediation hint | Sprint 12 |
| NFR-6 | Maintainability: ≥80% line coverage; mypy strict | All sprints |
| NFR-7 | Platform: Python 3.9+, macOS / Linux / Windows | CI matrix |

---

## 7. Data Model (Pydantic v2)

All entities live in `src/open_ats/models.py` (created Sprint 1). Code below is normative — implementations MUST match field names, types, and validators.

```python
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


# ── Resume entities ──

class SectionType(str, Enum):
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    PUBLICATIONS = "publications"
    AWARDS = "awards"
    OTHER = "other"


class Contact(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    website: Optional[HttpUrl] = None


class ExperienceEntry(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None  # ISO-ish; accept "2023-03", "March 2023", "2023"
    end_date: Optional[str] = None    # or "Present"
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    institution: str
    location: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[float] = None
    coursework: list[str] = Field(default_factory=list)


class Section(BaseModel):
    type: SectionType
    raw_heading: str          # the literal heading text in the source (e.g. "Work Experience")
    body: str                 # raw section text, post-extraction
    bullets: list[str] = Field(default_factory=list)


class ParserWarning(BaseModel):
    code: str                 # e.g. "formatting.table_detected"
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class Resume(BaseModel):
    source_path: Optional[Path] = None
    source_format: Literal["markdown", "docx", "pdf", "txt"]
    contact: Contact
    summary: Optional[str] = None
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    word_count: int = 0
    parser_warnings: list[ParserWarning] = Field(default_factory=list)


# ── Job description ──

class JobDescription(BaseModel):
    source_path: Optional[Path] = None
    title: Optional[str] = None
    company: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)  # "nice to have" / "bonus"
    keywords: list["Keyword"] = Field(default_factory=list)
    raw_text: str = ""
    parser_warnings: list[ParserWarning] = Field(default_factory=list)


# ── Keyword matching ──

class KeywordCategory(str, Enum):
    HARD_SKILL = "hard_skill"
    SOFT_SKILL = "soft_skill"
    ACTION_VERB = "action_verb"
    INDUSTRY_TERM = "industry_term"


class Keyword(BaseModel):
    canonical: str            # canonical spelling, e.g. "PostgreSQL"
    category: KeywordCategory
    synonyms: list[str] = Field(default_factory=list)
    matched: bool = False
    match_count: int = 0


# ── Analyzer outputs ──

class AnalyzerResult(BaseModel):
    analyzer: str             # "keyword" / "quantification" / "formatting" / "content_quality"
    score: float = Field(ge=0.0, le=100.0)
    sub_scores: dict[str, float] = Field(default_factory=dict)
    matched_items: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


# ── Scoring ──

RoleLevel = Literal["entry", "mid", "senior", "executive"]


class ScoringConfig(BaseModel):
    role_level: RoleLevel = "mid"
    weights: dict[str, float]  # {"keyword": 0.40, "quantification": 0.20, ...}
    industry: Optional[str] = None
    custom_keyword_db: Optional[Path] = None


class CategoryScore(BaseModel):
    name: str                 # "keyword" / "quantification" / "formatting" / "content_quality"
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0)
    contribution: float       # score * weight
    sub_scores: dict[str, float] = Field(default_factory=dict)


class FormulaAuditEntry(BaseModel):
    step: str                 # human-readable description
    formula: str              # e.g. "0.40 * 72.5"
    inputs: dict[str, float]
    output: float


class Recommendation(BaseModel):
    category: str
    severity: Literal["info", "low", "medium", "high"]
    message: str              # actionable; never just observational
    expected_score_impact: float = Field(ge=0.0, le=100.0)
    related_items: list[str] = Field(default_factory=list)


class Rating(str, Enum):
    EXCELLENT = "excellent"  # 80-100
    GOOD = "good"            # 70-79
    FAIR = "fair"            # 60-69
    POOR = "poor"            # 0-59


class Score(BaseModel):
    overall: float = Field(ge=0.0, le=100.0)
    rating: Rating
    categories: list[CategoryScore]
    formula_audit: list[FormulaAuditEntry]
    recommendations: list[Recommendation] = Field(default_factory=list)


# ── Scan result ──

class ScanResult(BaseModel):
    scan_id: str              # UUID4
    timestamp: datetime
    open_ats_version: str
    resume_hash: str          # SHA-256 of resume bytes
    jd_hash: str              # SHA-256 of JD bytes
    resume: Resume
    job_description: JobDescription
    analyzer_results: list[AnalyzerResult]
    score: Score
    config: ScoringConfig


# ── Audit trail ──

class AuditEntry(BaseModel):
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
    # full ScanResult is stored as a JSON column; AuditEntry is the index row
```

---

## 8. Scoring Formulas

### Overall

```
overall = Σ ( category.score × category.weight )

For role_level="mid" (defaults):
  overall = 0.40 × keyword.score
         + 0.20 × quantification.score
         + 0.20 × formatting.score
         + 0.20 × content_quality.score
```

Every step lands in `Score.formula_audit` so a reader can reconstruct the result.

### Keyword sub-scores (FR-3, Sprint 5)

```
keyword.score = 0.50 × hard_skills_score
             + 0.25 × soft_skills_score
             + 0.15 × action_verbs_score
             + 0.10 × industry_terms_score

each subscore = min(100, 100 × matched_unique / max(1, expected_unique))
```

### Quantification (FR-4, Sprint 6)

```
target_rate by role_level:
  entry: 0.50
  mid:   0.60
  senior: 0.55
  executive: 0.40

actual_rate = quantified_bullets / total_bullets

quantification.score = min(100, 100 × actual_rate / target_rate)
```

### Formatting (FR-5, Sprint 7)

```
formatting.score = max(0, 100 - Σ penalties)
```

### Content quality (FR-6, Sprint 7)

```
content_quality.score = 0.40 × action_verb_strength
                     + 0.30 × (100 - passive_voice_density × 100)
                     + 0.20 × (100 - hedging_density × 100)
                     + 0.10 × word_count_fitness
```

### Worked example

Mid-level resume with: keyword=72.0, quantification=58.0, formatting=85.0, content_quality=78.0

```
overall = 0.40×72.0 + 0.20×58.0 + 0.20×85.0 + 0.20×78.0
        = 28.80    + 11.60    + 17.00    + 15.60
        = 73.0
rating = GOOD (70–79)
```

The `formula_audit` for this scan would contain at minimum:
```
[
  {step: "keyword.contribution",       formula: "0.40 * 72.0", inputs: {weight: 0.40, score: 72.0}, output: 28.8},
  {step: "quantification.contribution", formula: "0.20 * 58.0", inputs: {weight: 0.20, score: 58.0}, output: 11.6},
  {step: "formatting.contribution",     formula: "0.20 * 85.0", inputs: {weight: 0.20, score: 85.0}, output: 17.0},
  {step: "content_quality.contribution", formula: "0.20 * 78.0", inputs: {weight: 0.20, score: 78.0}, output: 15.6},
  {step: "overall",                    formula: "sum of contributions", inputs: {...}, output: 73.0}
]
```

---

## 9. Regex Patterns — Quantification Detection (FR-4, Sprint 6)

These patterns ship in `src/open_ats/data/quantification_patterns.yaml` and are loaded by `QuantificationAnalyzer`. Each pattern has a name and is applied case-insensitively unless noted.

| Name | Pattern (Python regex) | Matches |
|---|---|---|
| `dollar_amount` | `\$\s?\d{1,3}(?:[,]\d{3})*(?:\.\d+)?\s?[KMBkmb]?\b` | $1.2M, $400K, $1,200,000.50 |
| `percentage` | `\b\d+(?:\.\d+)?\s?%` | 35%, 22.5% |
| `time_range_years` | `\b\d+\+?\s*(?:years?|yrs?)\b` | 5 years, 10+ yrs |
| `time_range_months` | `\b\d+\+?\s*(?:months?|mos?)\b` | 6 months, 18+ mo |
| `multiplier` | `\b\d+(?:\.\d+)?\s?[xX]\b` | 11x, 2.5x |
| `headcount` | `\b(?:team\s+of|managed|led|hired|grew)\s+\d+\+?\b` | team of 12, hired 8 |
| `large_count` | `\b\d{1,3}(?:[,]\d{3})+\b` | 18,000, 1,200,000 |
| `frequency_per_unit` | `\b\d+(?:\.\d+)?[KkMm]?(?:[/]| per )(?:second|sec|minute|min|hour|hr|day|month|year)\b` | 80K/sec, 4TB/day |
| `rank_or_position` | `\b(?:top|first|#)\s?\d+(?:%|\b)` | top 5%, #1, first 10 |
| `data_volume` | `\b\d+(?:\.\d+)?\s?(?:KB|MB|GB|TB|PB)\b` | 4TB, 250GB |

A bullet is flagged as quantified if **any** pattern matches.

---

## 10. Word Lists (FR-6, Sprint 7)

These ship in `src/open_ats/data/`. Sprint 7 lands them; Sprint 0 specifies content.

### 10.1 Strong action verbs (`action_verbs.yaml`, ≥50)

Achieved, Architected, Authored, Automated, Built, Coached, Collaborated, Conceived, Crafted, Created, Decreased, Defined, Delivered, Designed, Developed, Drove, Eliminated, Engineered, Established, Executed, Expanded, Generated, Grew, Guided, Hired, Implemented, Improved, Increased, Influenced, Initiated, Innovated, Instituted, Introduced, Invented, Launched, Led, Managed, Mentored, Migrated, Negotiated, Optimized, Orchestrated, Originated, Owned, Pioneered, Produced, Reduced, Refactored, Resolved, Restructured, Revamped, Saved, Scaled, Secured, Shipped, Simplified, Spearheaded, Standardized, Streamlined, Strengthened, Tripled, Unified

### 10.2 Weak verbs (`weak_verbs.yaml`, ≥30)

Assisted, Attempted, Compiled, Conducted, Considered, Contributed, Coordinated, Handled, Helped, Investigated, Managed-routine, Monitored, Observed, Participated, Performed, Provided, Reviewed, Saw, Studied, Supported, Tasked, Took-part, Tracked, Utilized, Was-responsible-for, Watched, Worked, Worked-on, Worked-with, Wrote-some

### 10.3 Passive-voice markers (`passive_markers.yaml`, ≥15)

Used `to be` + past-participle constructions plus heuristic markers:
- "was responsible for"
- "were tasked with"
- "is being"
- "was being"
- "have been"
- "had been"
- "got assigned"
- "was given"
- "were asked to"
- "it was decided"
- "is performed"
- "are managed"
- "were created"
- "was implemented"
- "has been carried out"

(spaCy dependency parser supplements these for higher recall in Sprint 7.)

### 10.4 Hedging language (`hedging.yaml`, ≥10)

- "Helped to"
- "Tried to"
- "Worked on"
- "Was involved in"
- "Participated in"
- "Familiar with"
- "Exposed to"
- "Some experience with"
- "Basic understanding of"
- "Working knowledge of"
- "Have used"
- "Have worked with"

---

## 11. Reports

### 11.1 JSON report (FR-8, Sprint 5)

The JSON report is the canonical machine-readable form. Fields exactly mirror `ScanResult` (§7) with `pydantic.BaseModel.model_dump_json(indent=2, sort_keys=True)` — sorted keys for byte-stable output.

### 11.2 HTML report (FR-8, Sprint 9)

Single-file HTML. Top-level structure:

```
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Open ATS Scan — {timestamp}</title>
    <style>/* scoped CSS, no external deps */</style>
  </head>
  <body>
    <header>Score: {overall} / 100 — {rating}</header>
    <section id="categories">…each CategoryScore…</section>
    <section id="recommendations">…actionable items, sorted by expected_score_impact desc…</section>
    <section id="formula-audit"><details><summary>Show formulas</summary>…</details></section>
    <section id="metadata">scan_id, version, hashes</section>
  </body>
</html>
```

Constraints: ≤500KB, W3C-valid, no JavaScript required for viewing, alt text on all visual elements, color-contrast AAA on score regions.

---

## 12. Audit-Trail Schema (FR-9, Sprint 10)

Default DB: `~/.open-ats/audit.db` (SQLite). Schema:

```sql
CREATE TABLE IF NOT EXISTS scans (
    scan_id           TEXT PRIMARY KEY,
    timestamp         TEXT NOT NULL,
    resume_path       TEXT NOT NULL,
    jd_path           TEXT NOT NULL,
    resume_hash       TEXT NOT NULL,
    jd_hash           TEXT NOT NULL,
    score_overall     REAL NOT NULL,
    score_rating      TEXT NOT NULL,
    role_level        TEXT NOT NULL,
    open_ats_version  TEXT NOT NULL,
    scan_result_json  TEXT NOT NULL  -- full ScanResult as JSON
);

CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp);
CREATE INDEX IF NOT EXISTS idx_scans_resume_hash ON scans(resume_hash);
CREATE INDEX IF NOT EXISTS idx_scans_jd_hash ON scans(jd_hash);
```

Compare semantics: `compare(from_id, to_id)` produces a delta diff highlighting score deltas, recommendation set differences, and matched-keyword changes.

---

## 13. Workflows

### Single scan
```
user → CLI scan → parse_resume → parse_jd
                              → analyzers (keyword, quant, formatting, content)
                              → ScoringEngine
                              → Reporter (json|html)
                              → AuditTrail.persist(ScanResult)
                              → exit 0, write report
```

### Batch
```
user → CLI batch --resume-dir D --jd JD --output-dir OUT
       → for resume in D: single-scan → write OUT/<resume_basename>.{json,html}
       → emit summary (count, mean overall, rating distribution)
```

### Compare
```
user → CLI compare --from ID1 --to ID2 [--output OUT.html]
       → AuditTrail.fetch(ID1, ID2)
       → Differ produces delta payload (score, recommendations, keyword set)
       → Reporter renders compare report
```

---

## 14. Testing Strategy (cross-reference)

Detailed strategy lives in `docs/testing-strategy.md` (Sprint 11). The PRD specifies *what* must pass:

- **Unit:** ≥80% line coverage per module touched in a sprint
- **Integration:** parser ↔ analyzer pairs covered for each format/analyzer combination
- **E2E:** CLI invocation → file output for every command introduced
- **Validation:** golden cases (Sprint 11), idempotency (100 runs, 0 diffs), performance gates (NFR-1)
- **Security:** gstack `/cso` clean for each PR touching parsing or audit-trail (Sprint 12 + ad hoc)
- **Correlation:** ≥0.90 Pearson on JobScan holdout (Sprint 13 only)

---

## 15. Deployment

MVP through v0.4.0 ships as a Python package:

```
pip install open-ats-scanner   # PyPI publish in Sprint 13 prep
```

No server, no database (audit trail is local SQLite). v1.2 adds an optional FastAPI web wrapper (out of scope).

---

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PDF parsing fragility | High | Med | Curated fixtures first; fail loudly on image-based; capture real-world failures as new fixtures |
| 90% JobScan correlation unreachable | Med | High | Gate to v1.0 only; document achievable r as the public benchmark |
| Word lists become contentious (which verbs are "weak"?) | Med | Low | Cite sources in YAML metadata; treat lists as configurable |
| spaCy model size in CI / install footprint | Med | Med | Pin a small model (`en_core_web_sm`); document install step |
| Solo-dev sprint chain stalls mid-roadmap | Med | Med | Each release tag (v0.2/0.3/0.4) is independently shippable |
| Audit DB corruption | Low | High | Hash-based integrity check on read; export/import JSON path |

---

## 17. Glossary

- **ATS** — Applicant Tracking System. Software employers use to filter resumes.
- **Audit trail** — Time-ordered history of scans for a given user, with full inputs and outputs preserved.
- **Formula audit** — Per-scan record of every numerical step that produced the score.
- **Golden case** — Hand-curated `(resume, JD, expected_score, expected_recommendations)` tuple used as a regression gate.
- **Quantified bullet** — A resume bullet containing at least one numerical metric (matched by `quantification_patterns.yaml`).
- **Role level** — One of `entry`, `mid`, `senior`, `executive`; selects a weight preset.
- **Sprint contract** — `.context/sprints/NN-contract.md`; the negotiated scope and grading rubric for a single sprint.
- **Evaluator** — A separate Claude Code session that grades sprint output against the contract; never the same session that implemented the code.

---

## 18. Document History

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-08 | Initial commit | Stub PRD pointing at conversation history. |
| 1.0 | 2026-05-08 | Sprint 0 | Full expansion: G/W/T criteria, Pydantic models, regex patterns, word lists, scoring formulas with worked examples, report and audit schemas. |

---

## Appendix A — Sample Score Walkthrough on Fixtures

Using `tests/fixtures/resumes/mid_level.md` against `tests/fixtures/job_descriptions/mid_level_backend.txt`, the expected behavior in v0.2.0 (after Sprint 5):

- Hard-skill matches: Python, AWS, PostgreSQL, Redis, Docker, Terraform → 6 of ~10 expected → `hard_skills` score ≈ 60
- Soft-skill matches: mentorship, code review, written communication → ~3 of ~5 → `soft_skills` ≈ 60
- Action-verb matches: led, scaled, mentored, drove, owned, designed, built, reduced → 8 of ~50 (broad list) → strength score ≈ 70
- Industry terms: SLO, design RFC, observability, postmortem → ~4 of ~10 → `industry_terms` ≈ 40

Aggregate keyword score (after Sprint 5): roughly 60.

The full overall score arrives once Sprints 6–8 complete; the worked example in §8 mirrors that future state.

---

**End of PRD v1.0.**
