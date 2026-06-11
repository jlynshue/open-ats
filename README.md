# Open ATS Resume Scanner

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![PyPI](https://img.shields.io/badge/pypi-open--ats--scanner-blue)](https://pypi.org/project/open-ats-scanner/)

**Transparent, Unlimited, Open-Source ATS Resume Scanning Tool**

A comprehensive resume scanner that emulates commercial ATS tools while providing transparent scoring, complete audit trails, and proof of improvement tracking. Zero black boxes. Unlimited scans. Complete version control.

## Features

- **Transparent Scoring** — All formulas and calculations are visible and auditable
- **Unlimited Scans** — No monthly limits like commercial tools
- **Complete Audit Trail** — Track improvements over time with full version control
- **Multiple Formats** — Markdown, DOCX, PDF, and plain text resumes
- **Actionable Recommendations** — Prioritized suggestions with expected score impact
- **Configurable Weights** — Customize scoring for different job levels (entry, mid, senior, executive)

## Quick Start

### Installation

```bash
# Install from PyPI
pip install open-ats-scanner

# Or install from source
git clone https://github.com/jlynshue/open-ats.git
cd open-ats
pip install -e .
```

### Usage

```bash
# Scan a single resume
open-ats scan \
    --resume resume.md \
    --job-description jd.txt \
    --output report.html

# Batch scan multiple resumes
open-ats batch \
    --resume-dir resumes/ \
    --job-description jd.txt \
    --output-dir reports/

# Compare two scans to track improvement
open-ats compare \
    --from-scan scan_id_1 \
    --to-scan scan_id_2 \
    --output improvement_report.html
```

## How It Works

```
Resume Input → Parser → Keyword Matcher → Scorer → Report Generator
                (DOCX/PDF/MD/TXT)  (NLP-based)    (transparent)   (HTML/JSON)
```

### Scoring Pipeline

**1. Parse Resume & Job Description**
Extract structured data using NLP techniques with format detection.

**2. Analyze & Match**
- **Keyword Matching:** Hard skills, soft skills, action verbs, industry keywords
- **Quantification:** Identify achievements with metrics (15%, $1.4B, 10 years)
- **Formatting:** Detect ATS-breaking elements (tables, special characters)
- **Content Quality:** Weak verbs, passive voice, hedging language detection

**3. Score with Transparent Formulas**

```
Overall Score = Σ(Category Score × Weight)

Default Weights:
  Keyword Match:    40%
  Quantification:   20%
  Formatting:       20%
  Content Quality:  20%
```

Each formula is documented and auditable. See [Scoring System](docs/scoring-system.md) for full details.

**4. Generate Report & Track Improvement**
- Detailed HTML/JSON reports with actionable recommendations
- Complete audit trail showing score progression
- Before/after comparisons proving improvement

## Why Open ATS?

### Commercial Tool Comparison

| Feature | JobScan | Resume Worded | Open ATS |
|---------|---------|---------------|----------|
| Free scans/month | 5 | 2-3 | ∞ Unlimited |
| Scoring transparency | ❌ Black box | ❌ Black box | ✅ Open formulas |
| Audit trail | ⚠️ Limited | ⚠️ Limited | ✅ Complete |
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

## Validation & Correlation

**Target:** 90%+ correlation with JobScan on standard resume/JD pairs.

**Methodology:**
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
