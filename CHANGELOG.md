# Changelog

All notable changes to Open ATS Resume Scanner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Sprint 1 — Markdown Resume Parser)
- `src/open_ats/models.py` — Pydantic v2 entity definitions per PRD §7 (Resume, Contact, Section, ExperienceEntry, EducationEntry, JobDescription, Keyword, ScanResult, Score, CategoryScore, Recommendation, AuditEntry, ScoringConfig, plus enums)
- `src/open_ats/parsers/base.py` — `Parser` Protocol, `ResumeParseError`, `UnsupportedFormatError`, shared regex helpers (email/phone/linkedin/github extraction), `classify_section_heading` heading→`SectionType` classifier
- `src/open_ats/parsers/markdown_parser.py` — `MarkdownParser` with heading-driven section detection, contact extraction, experience/education/skills extraction, ParserWarning emission for missing email/short resumes/invalid URLs
- `src/open_ats/parsers/__init__.py` — `parse_resume(path)` extension dispatcher (`.md` and `.markdown` wired)
- `tests/unit/test_markdown_parser.py` — 46 tests covering all FR-1.1 acceptance criteria, edge cases (empty file, malformed email, heading aliases), and determinism
- 2 new fixtures: `tests/fixtures/resumes/no_email.md`, `tests/fixtures/resumes/minimal.md`
- `pyproject.toml` — `pydantic[email]` extra (enables `EmailStr` validation via `email-validator`)

### Changed
- Test-fixture emails: `@example.test` → `@example.com` (email-validator rejects the reserved `.test` TLD)
- README "Phase 1 (MVP)" status: Markdown parsing now checked off

### Fixed
- `.gitignore`: root-anchor `/resumes/` and `/job_descriptions/` (was matching `tests/fixtures/resumes/` and `tests/fixtures/job_descriptions/`, silently dropping all 6 fixtures from Sprint 0's PR). Sprint 1 brings the recovered fixtures along.

### Added (Sprint 0 — Spec, Scaffold, Decisions)
- `LICENSE` (MIT) at repo root; matches `pyproject.toml`
- Full PRD (`docs/PRD.md`): Given/When/Then acceptance criteria for FR-1..FR-10, Pydantic v2 entity definitions, regex patterns for quantification detection, word lists (≥50 strong action verbs / ≥30 weak verbs / ≥15 passive markers / ≥10 hedging phrases), scoring formulas with worked examples, JSON/HTML report schemas, audit-trail SQLite schema, role-level weight presets
- `src/open_ats/{parsers,analyzers,scoring,reporting,audit_trail,cli,data}/` package skeleton with stub `__init__.py` per layer
- `src/open_ats/cli/main.py` click entry point (commands implemented in Sprints 5+)
- `tests/{unit,integration,e2e,validation,fixtures}/` directory tree + `tests/conftest.py` with path-helper fixtures
- 3 hand-crafted Markdown resume fixtures (entry, mid, executive) + 3 matching JDs
- `keyword_databases/_template.yaml` and `keyword_databases/software_engineering.yaml` (~70-entry seed)
- `.github/workflows/ci.yml` — GitHub Actions: lint (ruff + black), typecheck (mypy), test matrix (Python 3.9–3.12)
- `.pre-commit-config.yaml` — ruff, black, mypy hooks
- `.context/sprints/00-contract.md` — negotiated Sprint 0 scope and grading thresholds

### Changed
- `README.md` — project structure section corrected to `src/open_ats/...` layout; `[PLACEHOLDER]` markers replaced with `MIT` and concrete GitHub org
- `CLAUDE.md` — project structure section corrected; console-script note added
- `pyproject.toml` — `[PLACEHOLDER: Confirm license]` comment removed (MIT confirmed); minimum Python bumped from 3.9 → 3.10 (3.9 reached end-of-life Oct 2025 and is no longer a mypy target); ruff config migrated from top-level `select`/`ignore` to `[tool.ruff.lint]` section
- `.github/workflows/ci.yml` — test matrix dropped 3.9, kept 3.10–3.12

### Planning (carried from prior `[Unreleased]`)
- Multi-sprint roadmap (S0–S13) mapped to releases v0.2 → v1.0 in `~/.claude/plans/system-instruction-you-are-working-curried-eagle.md`
- Harness methodology (Planner → Generator → Evaluator) applied per sprint with separate evaluator sessions and concrete grading rubrics

## [0.1.0] - 2026-05-08

### Added
- Initial project setup
- Project structure and directory layout
- README with project overview and roadmap
- PRD (Product Requirements Document)
- pyproject.toml with dependencies
- .gitignore for Python project
- CHANGELOG.md (this file)
- Git repository initialization

### Documentation
- Complete PRD with 100+ pages of specifications
- Scoring system documentation
- Testing strategy documentation
- Data model definitions
- Workflow diagrams

---

## Release Planning

### [0.2.0] - MVP Alpha (Target: Q2 2026)
**Focus:** Core scanning functionality, CLI interface

#### Planned Features
- [ ] Resume parsing (Markdown, DOCX, PDF, plain text)
- [ ] Job description parsing
- [ ] Keyword extraction and matching
- [ ] Quantification rate calculation
- [ ] Basic formatting validation
- [ ] ATS compatibility scoring (0-100)
- [ ] JSON report generation
- [ ] Basic CLI interface
- [ ] Unit test suite (50%+ coverage)

### [0.3.0] - MVP Beta (Target: Q2 2026)
**Focus:** Complete audit trail, HTML reports, testing

#### Planned Features
- [ ] Complete audit trail implementation
- [ ] HTML report generation
- [ ] Improvement tracking and comparison
- [ ] Content quality analysis (weak verbs, passive voice)
- [ ] Comprehensive test suite (80%+ coverage)
- [ ] Documentation improvements

### [0.4.0] - MVP Release Candidate (Target: Q2 2026)
**Focus:** Validation, performance, polish

#### Planned Features
- [ ] Validation testing against JobScan (90%+ correlation target)
- [ ] Performance optimization (<5 sec scan time)
- [ ] Batch scanning mode
- [ ] Configuration file support
- [ ] Error handling improvements
- [ ] User documentation

### [1.0.0] - Production Release (Target: Q3 2026)
**Focus:** Stable, production-ready scanner

#### Planned Features
- [ ] 90%+ scoring correlation with JobScan validated
- [ ] Complete test coverage (80%+)
- [ ] Performance targets met
- [ ] All MVP features complete and tested
- [ ] Comprehensive documentation
- [ ] PyPI package publication

### [1.1.0] - Enhancement Release (Target: Q3 2026)
**Focus:** Advanced NLP, customization

#### Planned Features
- [ ] Semantic keyword matching
- [ ] Synonym detection
- [ ] Industry-specific keyword databases
- [ ] Role-level scoring customization (entry, mid, senior, exec)
- [ ] Section-level analysis
- [ ] PDF report generation

### [1.2.0] - Web Interface (Target: Q4 2026)
**Focus:** Web UI, multi-user support

#### Planned Features
- [ ] FastAPI web backend
- [ ] Web UI for resume upload and JD entry
- [ ] Visual audit trail (charts, graphs)
- [ ] User authentication (optional)
- [ ] API endpoints for third-party integration

### [2.0.0] - Advanced Features (Target: Q4 2026)
**Focus:** ML optimization, enterprise features

#### Planned Features
- [ ] Machine learning scoring optimization
- [ ] ATS vendor-specific profiles (Taleo, Workday, Greenhouse)
- [ ] Multi-language support
- [ ] Cover letter analysis
- [ ] LinkedIn profile optimization

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this changelog and the project.

## Versioning

- **Major version (X.0.0):** Breaking changes, major new features
- **Minor version (0.X.0):** New features, backward-compatible
- **Patch version (0.0.X):** Bug fixes, minor improvements
