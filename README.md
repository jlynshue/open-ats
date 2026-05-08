# Open ATS Resume Scanner

**Transparent, Unlimited, Open-Source ATS Resume Scanning Tool**

A comprehensive resume scanner that emulates commercial ATS tools while providing transparent scoring, complete audit trails, and proof of improvement tracking.

## Features

- ✅ **Transparent Scoring** - All formulas and calculations are visible and auditable
- ✅ **Unlimited Scans** - No monthly limits like commercial tools 
- ✅ **Complete Audit Trail** - Track improvements over time with version control
- ✅ **Multiple Formats** - Support for Markdown, DOCX, PDF, and plain text resumes
- ✅ **Actionable Recommendations** - Prioritized suggestions with expected score impact
- ✅ **Configurable Weights** - Customize scoring for different job levels (entry, mid, senior, executive)

## Quick Start

### Installation

```bash
# Install from PyPI (coming soon)
pip install open-ats-scanner

# Or install from source
git clone https://github.com/jlynshue/open-ats.git
cd open-ats
pip install -e .
```

### Basic Usage

```bash
# Run a single scan
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

## Project Status

**Phase 1 (MVP) - In Development**

- [x] Resume parsing — Markdown (Sprint 1)
- [x] Resume parsing — DOCX, TXT (Sprint 2)
- [ ] Resume parsing — PDF (Sprint 3)
- [ ] Job description parsing
- [ ] Keyword matching analysis
- [ ] Quantification rate calculation
- [ ] Formatting validation
- [ ] ATS compatibility scoring (0-100)
- [ ] Detailed JSON/HTML reports
- [ ] Basic audit trail
- [ ] CLI interface

**Phase 2 (Enhancement) - Planned**

- [ ] Advanced NLP (semantic matching, synonym detection)
- [ ] Section-level analysis
- [ ] Industry-specific keyword databases
- [ ] Role-level customization
- [ ] Visual audit trail (charts)
- [ ] Web interface
- [ ] PDF report generation

## Documentation

- [Product Requirements Document (PRD)](docs/PRD.md) - Complete specifications
- [Scoring System](docs/scoring-system.md) - Transparent formulas and calculations
- [Testing Strategy](docs/testing-strategy.md) - Comprehensive test plans
- [API Reference](docs/api-reference.md) - Developer documentation

## Project Structure

```
open-ats/
├── src/open_ats/          # Python package (import root: `open_ats`)
│   ├── parsers/           # Resume and JD parsing (Markdown, DOCX, PDF, TXT)
│   ├── analyzers/         # Keyword, quantification, formatting, content quality
│   ├── scoring/           # Transparent scoring engine
│   ├── reporting/         # JSON / HTML / PDF report generation
│   ├── audit_trail/       # Scan history, version control, improvement tracking
│   ├── cli/               # `open-ats` command-line entry point
│   └── data/              # Bundled word lists and presets
├── tests/
│   ├── unit/              # Unit tests (≥80% coverage target)
│   ├── integration/       # Integration tests across modules
│   ├── e2e/               # End-to-end CLI tests
│   ├── validation/        # Golden cases, idempotency, performance, correlation
│   └── fixtures/          # Sample resumes and job descriptions
├── docs/                  # PRD, scoring system, testing strategy, API reference
├── keyword_databases/     # Industry-specific keyword lists (YAML)
└── examples/              # Example workflows and sample data (added in Sprint 12)
```

## How It Works

### 1. Parse Resume & Job Description

Extract structured data from resume and job description using NLP techniques.

### 2. Analyze & Match

- **Keyword Matching:** Hard skills, soft skills, action verbs, industry keywords
- **Quantification:** Identify achievements with metrics ($1.4B, 15%, 10 years)
- **Formatting:** Detect ATS-breaking elements (tables, special characters)
- **Content Quality:** Check for weak verbs, passive voice, hedging language

### 3. Score with Transparent Formulas

```
Overall Score = Σ(Category Score × Weight)

Default Weights:
  Keyword Match:    40%
  Quantification:   20%
  Formatting:       20%
  Content Quality:  20%

Each formula is documented and auditable.
```

### 4. Generate Report & Track Improvement

- Detailed HTML/JSON reports with actionable recommendations
- Complete audit trail showing score progression
- Before/after comparisons proving improvement

## Scoring Correlation

Target: **90%+ correlation** with commercial tools like JobScan

Validation methodology:
- 100 resume/JD pair test dataset
- Parallel scoring against JobScan
- Statistical analysis (Pearson correlation)
- Continuous refinement of weights and algorithms

## Why Open ATS?

### Commercial Tool Limitations

| Feature | JobScan | Resume Worded | Open ATS |
|---------|---------|---------------|----------|
| Free scans/month | 5 | 2-3 | ∞ Unlimited |
| Scoring transparency | ❌ Black box | ❌ Black box | ✅ Open formulas |
| Audit trail | ⚠️ Limited | ⚠️ Limited | ✅ Complete |
| Customization | ❌ Fixed | ❌ Fixed | ✅ Configurable |
| Cost | $50-90/mo | $49/mo | ✅ Free |

### Transparent Scoring

All formulas, weights, and calculations are documented and visible in reports. No black-box algorithms.

### Proof of Improvement

Complete version control and audit trails show exactly how your resume improved over time, with effectiveness metrics for each recommendation.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas where we need help:
- Keyword database expansion (industry-specific terms)
- Resume parsing edge cases
- Scoring weight validation
- Documentation improvements
- Test coverage expansion

## License

MIT — see [LICENSE](LICENSE).

## Roadmap

### Q2 2026
- ✅ Complete PRD and specifications
- [ ] MVP implementation (CLI + core scoring)
- [ ] Validation testing (90%+ correlation target)
- [ ] Beta release

### Q3 2026
- [ ] Advanced NLP features
- [ ] Web interface
- [ ] Industry-specific keyword databases
- [ ] V1.0 release

### Q4 2026
- [ ] API for third-party integrations
- [ ] Multi-language support
- [ ] Machine learning scoring optimization

## Support

- [Documentation](docs/)
- [GitHub Issues](https://github.com/jlynshue/open-ats/issues)
- [Discussions](https://github.com/jlynshue/open-ats/discussions)

## Credits

Built by developers who were frustrated with expensive, opaque commercial ATS scanners. Inspired by the need for transparency and unlimited iteration during job searches.

## Acknowledgments

- JobScan, Resume Worded, Targeted Resume for establishing the category
- Open-source NLP libraries: spaCy, NLTK
- The job-seeking community for feedback and testing

---

**Status:** 🚧 Early Development - PRD Complete, Implementation Starting

**Last Updated:** 2026-05-08
