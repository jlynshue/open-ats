# CLAUDE.md - Open ATS Resume Scanner

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**Open ATS Resume Scanner** is an open-source, transparent alternative to commercial ATS scanning tools (JobScan, Resume Worded). It provides unlimited resume scans with visible scoring formulas, complete audit trails, and proof of improvement tracking.

## Quick Start

### Development Setup

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Running Scans

```bash
# Single scan (when implemented)
open-ats scan --resume resume.md --job-description jd.txt --output report.html

# Batch scan
open-ats batch --resume-dir resumes/ --job-description jd.txt --output-dir reports/

# Compare scans
open-ats compare --from-scan <id1> --to-scan <id2> --output improvement.html
```

## Project Structure

```
open-ats/
├── src/                    # Source code
│   ├── parsers/            # Resume and JD parsing
│   ├── analyzers/          # Keyword, quantification, formatting analysis
│   ├── scoring/            # Transparent scoring engine
│   ├── reporting/          # Report generation (JSON, HTML, PDF)
│   ├── audit_trail/        # Version control and improvement tracking
│   └── cli/                # Command-line interface
├── tests/                  # Test suite
│   ├── unit/               # Unit tests (80%+ coverage target)
│   ├── integration/        # Integration tests
│   ├── e2e/                # End-to-end tests
│   └── fixtures/           # Sample resumes and job descriptions
├── docs/                   # Documentation
│   ├── PRD.md              # Complete Product Requirements Document
│   └── [more docs TBD]
├── examples/               # Example resumes, JDs, configs
├── keyword_databases/      # Industry-specific keyword lists
└── config/                 # Default configuration files
```

## Development Workflow

### 1. Feature Development

When implementing features from the PRD:

1. **Read the PRD section** (`docs/PRD.md`) for the feature
2. **Create tests first** (TDD approach)
3. **Implement the feature**
4. **Update documentation**
5. **Run full test suite**

### 2. Testing Standards

- **Unit tests:** Test individual functions in isolation
- **Integration tests:** Test module interactions
- **E2E tests:** Test complete workflows (scan → report)
- **Coverage target:** 80%+ for new code
- **Mark slow tests:** Use `@pytest.mark.slow` for tests >1 second

Example:
```python
import pytest

def test_parse_markdown_resume():
    """Test parsing a well-formed Markdown resume."""
    resume = parse_resume("tests/fixtures/resumes/sample.md")
    assert resume.contact.email == "test@example.com"
    assert len(resume.experience) == 3

@pytest.mark.slow
def test_parse_large_pdf():
    """Test parsing a 10-page PDF resume."""
    resume = parse_resume("tests/fixtures/resumes/large.pdf")
    assert resume.word_count > 2000
```

### 3. Code Style

- **Python style:** Black (88 chars), Ruff linting
- **Type hints:** Required for all public functions
- **Docstrings:** Google style, required for public functions
- **Imports:** Sorted with isort (via Ruff)

Example:
```python
def calculate_keyword_match_score(
    resume_keywords: Set[str],
    jd_keywords: Set[str],
    config: ScoringConfig
) -> float:
    """Calculate keyword match score between resume and job description.
    
    Args:
        resume_keywords: Set of keywords extracted from resume
        jd_keywords: Set of keywords extracted from job description
        config: Scoring configuration with weights
    
    Returns:
        Keyword match score from 0-100
    
    Example:
        >>> resume_kw = {"Python", "AWS", "Docker"}
        >>> jd_kw = {"Python", "AWS", "Docker", "Kubernetes"}
        >>> score = calculate_keyword_match_score(resume_kw, jd_kw, config)
        >>> assert 0 <= score <= 100
    """
    # Implementation here
```

### 4. Commit Messages

Follow Conventional Commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Build/tool changes

Example:
```bash
git commit -m "feat: add PDF parsing with pdfplumber

- Implemented PDF text extraction
- Added support for multi-column layouts
- Handles password-protected PDFs gracefully
- Added 15 unit tests for edge cases

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Key Principles

### 1. Transparency First

All scoring formulas and calculations must be:
- Documented in code comments
- Visible in reports
- Auditable by users

**Example from PRD:**
```
Overall Score = Σ(Category Score × Weight)

Default Weights:
  Keyword Match:    40%
  Quantification:   20%
  Formatting:       20%
  Content Quality:  20%
```

### 2. Test-Driven Development

Write tests before implementation:
1. Write failing test
2. Implement feature
3. Verify test passes
4. Refactor if needed

### 3. Performance Targets

From PRD Section 6.2 (NFR-1):
- Resume parsing: <2 seconds for 2-page resume
- End-to-end scan: <5 seconds total
- Batch processing: >10 resumes/minute
- Memory usage: <500MB per scan

### 4. Validation Target

**90%+ correlation** with JobScan on 100 resume/JD test pairs

This is the North Star metric. All scoring decisions should optimize for this correlation while maintaining transparency.

## PRD Quick Reference

### Core Requirements

**FR-1:** Resume parsing (Markdown, DOCX, PDF, TXT) - 90%+ accuracy  
**FR-2:** Job description parsing with keyword extraction  
**FR-3:** Keyword matching (hard skills, soft skills, action verbs)  
**FR-4:** Quantification analysis (60% target for mid-level)  
**FR-5:** Formatting validation (detect ATS-breaking elements)  
**FR-6:** Content quality (weak verbs, passive voice, hedging)  
**FR-7:** Transparent scoring engine with configurable weights  
**FR-8:** Report generation (JSON, HTML, PDF)  
**FR-9:** Complete audit trail with version control  
**FR-10:** CLI interface (web UI in Phase 2)  

### Scoring Categories

1. **Keyword Match (40%):**
   - Hard skills: 50%
   - Soft skills: 25%
   - Action verbs: 15%
   - Industry keywords: 10%

2. **Quantification (20%):**
   - Target rate: 60% for mid-level, 40% for executive

3. **Formatting (20%):**
   - Penalty-based (start at 100, subtract for issues)
   - Tables: -10, Date inconsistency: -5, Special chars: -1

4. **Content Quality (20%):**
   - Action verb strength: 40%
   - Passive voice absence: 30%
   - Hedging language absence: 20%
   - Word count fitness: 10%

### Rating Thresholds

- **Excellent:** 80-100 (Submit with confidence)
- **Good:** 70-79 (Competitive, minor tweaks)
- **Fair:** 60-69 (Needs improvement)
- **Poor:** 0-59 (Major revision required)

## Common Tasks

### Adding a New Keyword Database

1. Create `keyword_databases/{industry}_keywords.yaml`
2. Follow format:
```yaml
hard_skills:
  - Python
  - AWS
soft_skills:
  - Leadership
industry_terms:
  - Data governance
```
3. Add tests in `tests/unit/test_keyword_extraction.py`
4. Update documentation

### Adding a New Resume Format

1. Create parser in `src/parsers/{format}_parser.py`
2. Implement `parse_resume(file_path: Path) -> Resume` interface
3. Add tests with fixtures in `tests/fixtures/resumes/`
4. Update `src/parsers/__init__.py` to register parser
5. Document supported formats in README

### Debugging Scoring Discrepancies

If scoring doesn't match JobScan:

1. Enable verbose logging
2. Compare intermediate scores (category by category)
3. Check keyword extraction (are we missing keywords?)
4. Verify quantification detection (regex patterns)
5. Review weight configuration
6. Add test case to validation suite

## Dependencies

### Core Dependencies

- **spaCy:** NLP for keyword extraction and entity recognition
- **NLTK:** Additional NLP utilities
- **python-docx:** DOCX parsing
- **pdfplumber:** PDF text extraction
- **Jinja2:** HTML report templating
- **click:** CLI framework
- **pydantic:** Data validation

### Dev Dependencies

- **pytest:** Testing framework
- **pytest-cov:** Coverage reporting
- **black:** Code formatting
- **ruff:** Linting
- **mypy:** Type checking

## Troubleshooting

### PDF Parsing Issues

- **Problem:** Text not extracted from PDF
- **Cause:** Image-based PDF (scanned document)
- **Solution:** Use OCR or ask user to convert to text-based PDF

### Keyword Matching Too Low

- **Problem:** Score too low compared to JobScan
- **Cause:** Missing synonyms or industry terms
- **Solution:** Expand keyword database, add synonym detection

### Memory Usage High

- **Problem:** Batch processing consumes >500MB per resume
- **Cause:** PDF objects not released
- **Solution:** Implement explicit cleanup, use context managers

## Resources

- **PRD:** `docs/PRD.md` - Complete specifications
- **Issues:** GitHub Issues for bug reports and feature requests
- **Discussions:** GitHub Discussions for questions
- **Contributing:** `CONTRIBUTING.md` for contribution guidelines

## Critical Rules

1. **DO NOT** implement features not in the PRD without discussion
2. **DO** write tests before implementation (TDD)
3. **DO** maintain 80%+ test coverage
4. **DO** document all scoring formulas transparently
5. **DO** optimize for 90%+ JobScan correlation
6. **DO NOT** compromise transparency for accuracy
7. **DO** validate all user inputs (security)
8. **DO** handle errors gracefully with actionable messages

## Contact

- **Repository:** https://github.com/jlynshue/open-ats
- **Maintainer:** Jonathan Lyn-Shue <jonathan.lynshue@gmail.com>

---

**Last Updated:** 2026-05-08  
**Project Phase:** Planning Complete, MVP Implementation Starting
