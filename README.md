# Open ATS Resume Scanner

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/jlynshue/open-ats/actions/workflows/ci.yml/badge.svg)](https://github.com/jlynshue/open-ats/actions/workflows/ci.yml)

**Transparent, Unlimited, Open-Source ATS Resume Scanning Tool**

A comprehensive resume scanner that emulates commercial ATS tools while providing transparent scoring, complete audit trails, and proof of improvement tracking. Zero black boxes. Unlimited scans. Complete version control.

## Features

- **Transparent Scoring** — All formulas and calculations are visible and auditable
- **Unlimited Scans** — No monthly limits like commercial tools
- **Complete Formula Audit** — Every scan emits a step-by-step audit of how the score was computed (cross-scan improvement tracking is planned)
- **Multiple Formats** — Markdown, DOCX, PDF, and plain text resumes
- **Actionable Recommendations** — Prioritized suggestions with expected score impact
- **Configurable Weights** — Customize scoring for different job levels (entry, mid, senior, executive)

## Quick Start

### Installation

```bash
# Install directly from GitHub
pip install git+https://github.com/jlynshue/open-ats.git

# Or install from source
git clone https://github.com/jlynshue/open-ats.git
cd open-ats
pip install -e .
```

### Basic Usage

```bash
# Scan a single resume (all formats: md, docx, pdf, txt)
open-ats scan \
    --resume resume.md \
    --job-description jd.txt \
    --output report.json
```

### Planned CLI Commands (Coming Soon)

These commands describe the planned CLI capabilities and will be available in future sprints:

```bash
# Planned (Sprint 9): HTML report output
open-ats scan \
    --resume resume.md \
    --job-description jd.txt \
    --output report.html

# Planned (Sprint 10): batch scan multiple resumes
open-ats batch \
    --resume-dir resumes/ \
    --job-description jd.txt \
    --output-dir reports/

# Planned (Sprint 10): compare two scans to track improvement
open-ats compare \
    --from-scan scan_id_1 \
    --to-scan scan_id_2 \
    --output improvement_report.html
```

## Example Output

```bash
$ open-ats scan \
    --resume resume.md \
    --job-description backend-engineer-jd.txt \
    --output report.json

Scanned resume.md against backend-engineer-jd.txt: score = 72.25 (good). Wrote report.json.
```

<details>
<summary>Sample JSON report (score breakdown)</summary>

```json
{
  "scan_id": "a3f7c2e1-9b4d-5a8f-b6c1-d4e2f0a8b5c7",
  "open_ats_version": "0.1.0",
  "score": {
    "overall": 72.25,
    "rating": "good",
    "categories": [
      {
        "name": "keyword",
        "score": 68.5,
        "weight": 0.5,
        "contribution": 34.25,
        "sub_scores": {
          "hard_skills": 72.73,
          "soft_skills": 66.67,
          "action_verbs": 80.0,
          "industry_terms": 50.0
        }
      },
      {
        "name": "formatting",
        "score": 90.0,
        "weight": 0.25,
        "contribution": 22.5,
        "sub_scores": {
          "starting_score": 100.0,
          "total_penalty": 10.0
        }
      },
      {
        "name": "content_quality",
        "score": 62.0,
        "weight": 0.25,
        "contribution": 15.5,
        "sub_scores": {
          "action_verb_strength": 58.33,
          "passive_voice_absence": 73.33,
          "hedging_absence": 80.0,
          "word_count_fitness": 100.0
        }
      }
    ],
    "formula_audit": [
      {
        "step": "keyword.contribution",
        "formula": "0.5 * 68.5",
        "inputs": { "weight": 0.5, "score": 68.5 },
        "output": 34.25
      },
      {
        "step": "formatting.contribution",
        "formula": "0.25 * 90.0",
        "inputs": { "weight": 0.25, "score": 90.0 },
        "output": 22.5
      },
      {
        "step": "content_quality.contribution",
        "formula": "0.25 * 62.0",
        "inputs": { "weight": 0.25, "score": 62.0 },
        "output": 15.5
      },
      {
        "step": "overall",
        "formula": "sum of category contributions",
        "inputs": { "keyword": 34.25, "formatting": 22.5, "content_quality": 15.5 },
        "output": 72.25
      }
    ],
    "recommendations": [
      {
        "category": "keyword",
        "severity": "high",
        "message": "Missing hard skills: Kubernetes, Terraform, gRPC. Add these to your experience bullets.",
        "expected_score_impact": 8.5
      },
      {
        "category": "content_quality",
        "severity": "medium",
        "message": "4/15 sentences use passive voice. Rewrite with active constructions.",
        "expected_score_impact": 3.2
      }
    ]
  },
  "config": {
    "role_level": "mid",
    "weights": {
      "keyword": 0.5,
      "formatting": 0.25,
      "content_quality": 0.25
    }
  }
}
```

</details>

## How It Works

```
Resume Input → Parser → Keyword Matcher → Scorer → Report Generator
                (DOCX/PDF/MD/TXT)  (NLP-based)    (transparent)   (JSON; HTML planned)
```

### Scoring Pipeline

**1. Parse Resume & Job Description**
Extract structured data using NLP techniques with format detection.

**2. Analyze & Match**
- **Keyword Matching:** Hard skills, soft skills, action verbs, industry keywords
- **Formatting:** Detect ATS-breaking elements (tables, special characters)
- **Content Quality:** Weak verbs, passive voice, hedging language detection
- **Quantification (planned):** Identify achievements with metrics (15%, $1.4B, 10 years)

**3. Score with Transparent Formulas**

```
Overall Score = Σ(Category Score × Weight)

Default Weights:
  Keyword Match:    50%
  Formatting:       25%
  Content Quality:  25%
```

Each formula is documented and auditable. See [Scoring System](docs/scoring-system.md) for full details.

**4. Generate Report & Track Improvement**
- Detailed JSON reports with a complete formula audit (HTML reports planned)
- Audit trail showing score progression (planned)
- Before/after comparisons proving improvement (planned)

## Why Open ATS?

Commercial ATS scanners charge $50-90/month for a black box that gives you a score with no explanation of how it was calculated. Open ATS takes the opposite approach: every formula, every weight, and every sub-score is visible and auditable. You get unlimited scans to iterate on your resume without hitting a paywall, and a complete audit trail that proves your improvements over time.

### Commercial Tool Comparison

| Feature | JobScan | Resume Worded | Open ATS |
|---------|---------|---------------|----------|
| Free scans/month | 5 | 2-3 | ∞ Unlimited |
| Scoring transparency | ❌ Black box | ❌ Black box | ✅ Open formulas |
| Per-scan formula audit | ❌ None | ❌ None | ✅ Complete |
| Cross-scan history / improvement tracking | ⚠️ Limited | ⚠️ Limited | 🔜 Planned |
| Customization | ❌ Fixed | ❌ Fixed | ✅ Configurable |
| Cost | $50-90/mo | $49/mo | ✅ Free |

### Philosophy

- **Transparent:** All algorithms visible. No black boxes.
- **Unlimited:** Iterate freely without subscription limits.
- **Open:** Community-driven development, MIT licensed.

## Project Structure

```
open-ats/
├── src/open_ats/          # Main package
│   ├── parsers/           # Resume & JD parsing
│   ├── analyzers/         # Keyword, quantification, formatting, quality
│   ├── scoring/           # Transparent scoring engine
│   ├── reporting/         # HTML/JSON report generation
│   ├── audit_trail/       # Scan history and improvement tracking
│   ├── cli/               # Command-line interface
│   └── data/              # Bundled word lists and presets
├── tests/
│   ├── unit/              # Unit tests (80%+ coverage target)
│   ├── integration/       # Cross-module integration tests
│   ├── e2e/               # End-to-end CLI tests
│   └── fixtures/          # Sample resumes and job descriptions
├── docs/                  # PRD, scoring, testing, API reference
├── keyword_databases/     # Industry-specific keyword lists (YAML)
└── examples/              # Example workflows and sample data
```

## Documentation

- **[Product Requirements Document](docs/PRD.md)** — Complete specifications and feature roadmap
- **[Scoring System](docs/scoring-system.md)** — Transparent formulas and calculations
- **[API Reference](docs/api-reference.md)** — Developer documentation
- **[Testing Strategy](docs/testing-strategy.md)** — Test plans and validation methodology
- **[Contributing Guide](CONTRIBUTING.md)** — How to contribute

## Validation & Correlation (planned)

> Status: not yet run. The figures below are a target and a proposed methodology, not measured results.

**Target:** 90%+ correlation with JobScan on standard resume/JD pairs.

**Proposed methodology:**
- 100 resume/JD pair test dataset
- Parallel scoring against JobScan
- Pearson correlation analysis
- Continuous refinement of weights

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas where we need help:
- Keyword database expansion (industry-specific terms)
- Resume parsing edge cases
- Scoring weight validation
- Test coverage expansion

## License

MIT — see [LICENSE](LICENSE)

## Support

- [GitHub Issues](https://github.com/jlynshue/open-ats/issues)
- [GitHub Discussions](https://github.com/jlynshue/open-ats/discussions)
- [Documentation](docs/)

---

## Author

**[Jonathan Lyn-Shue](https://jonathanlynshue.com)** — Fractional CIO/CTO | Data & AI Executive

Open ATS was built to solve a real problem: expensive, opaque commercial ATS scanners during job searches. It demonstrates principles I believe in across all technology: transparency, unlimited access, and user control.

**Last Updated:** 2026-06-11
