# Changelog

All notable changes to Open ATS Resume Scanner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Sprint 5 — Keyword Analyzer + First End-to-End CLI Slice)
- `src/open_ats/analyzers/base.py` — `Analyzer` Protocol + `AnalyzerError`. Every analyzer (keyword today; quantification / formatting / content quality in Sprints 6–7) implements `analyze(resume, jd) -> AnalyzerResult`.
- `src/open_ats/analyzers/_database.py` — `KeywordDatabase` loader for `keyword_databases/*.yaml` with case-insensitive lookup and synonym resolution. `load_default_database()` ships the bundled software-engineering seed; `load_databases([paths])` merges multiple files (first declaration wins).
- `src/open_ats/analyzers/keyword.py` — `KeywordAnalyzer` implementing PRD §FR-3 + §8 keyword formula: reclassify JD candidates against the database, drop unknowns, match against the resume haystack (case-insensitive substring with word-boundary for single-word tokens), compute four sub-scores (hard 50% / soft 25% / action 15% / industry 10%), and emit a complete `AnalyzerResult`. Action-verb scoring uses a bootstrap list of ~40 strong verbs (PRD §10.1 subset); Sprint 7 promotes this to `src/open_ats/data/action_verbs.yaml`.
- `src/open_ats/scoring/engine.py` — minimal `ScoringEngine` for Sprint 5: takes a list of `AnalyzerResult`s and produces a `Score` with one `CategoryScore` per analyzer, full `formula_audit`, rating derived per PRD §8 thresholds. Sprint 8 extends to multi-category weighted aggregation via role-level configs.
- `src/open_ats/reporting/json_report.py` — `render_json(scan_result)` and `write_json(scan_result, path)` produce byte-stable JSON with sorted keys for deterministic diffs across runs.
- `src/open_ats/cli/main.py` — replaced the Sprint-0 stub with the real `scan` command: `open-ats scan --resume X --job-description Y --output Z.json`. Builds a complete `ScanResult` with deterministic UUID + hashes + timestamp so two runs over identical inputs produce byte-identical reports.
- `tests/fixtures/golden/scores.yaml` — 5 (resume, JD, expected_score) tuples with ±5 tolerance covering matched and mismatched pairs.
- `tests/unit/test_keyword_analyzer.py` (18 tests), `tests/unit/test_scoring_engine.py` (10 tests), `tests/unit/test_json_report.py` (6 tests), `tests/e2e/test_cli_scan.py` (8 tests including the byte-identical determinism gate, golden-score sweep, and <3s perf gate).

### v0.2.0 — first releasable artifact
With Sprint 5, `open-ats scan` is end-to-end functional. Phase-1 input layer (resume + JD parsing) feeds the keyword analyzer; the scoring engine produces a transparent 0–100 Score with full formula audit; the JSON reporter writes bit-stable output. Sprints 6–10 add quantification / formatting / content-quality analyzers, multi-category aggregation, HTML reports, and the audit trail.

### Changed
- README "Phase 1 (MVP)" status: keyword matching, ATS scoring (keyword-only), JSON reports, and CLI all checked off.
- `pyproject.toml` mypy override: added `yaml` and `fpdf` to `ignore_missing_imports` (no upstream type stubs).

### Added (Sprint 4 — Job Description Parser)
- `src/open_ats/parsers/jd_parser.py` — `JdParser` + `parse_job_description(path_or_str)` top-level function. Walks JD lines detecting markdown or plain-text headings against a JD-specific alias map (Requirements / Required / Must have / Qualifications → `requirements`; What you'll do / The role → `responsibilities`; Nice to have / Bonus / Preferred → `preferences`; Benefits dropped). Extracts keyword candidates via rule-based passes: ALL-CAPS acronyms, multi-word title-case phrases, single proper nouns (with sentence-start filtering against a lowercase vocabulary), hyphenated lowercase compounds. Title and company extracted from the first non-empty line via `Title — Company` / `Title at Company` splitters.
- 2 new JD fixtures: `data_scientist.txt` (healthcare ML role) and `product_designer.txt` (B2B logistics design role) — total now 5 fixtures across SWE / backend / executive / data-science / design.
- `tests/fixtures/job_descriptions/_golden_keywords.yaml` — hand-annotated true-positive keyword set per fixture. Drives the FR-2 precision-≥80% gate via `test_keyword_precision_per_fixture` and the recall-≥40% sanity check.
- `tests/unit/test_jd_parser.py` (48 tests) — section split, preferences routing, per-fixture and aggregate keyword precision/recall, title + company extraction, too-short warning, raw-string vs path dispatch, error paths, determinism.

### Decisions
- **spaCy deferred to Sprint 5.** The plan called for "noun phrases via spaCy"; rule-based extraction is the simplest implementation that meets FR-2's precision-≥80% gate without dragging in a 12 MB model download. Sprint 5's keyword analyzer will introduce spaCy where its synonym normalisation and lemmatisation pay off for *matching*, not candidate generation.

### Changed
- README "Phase 1 (MVP)" status: Job description parsing checked off; FR-2 marked complete.

### Added (Sprint 3 — PDF Resume Parser)
- `src/open_ats/parsers/pdf_parser.py` — `PdfParser` opens `.pdf` via pdfplumber, extracts text page-by-page, raises `ResumeParseError("PDF appears to be image-based; please convert to text-based PDF")` (FR-1.3 verbatim) when extraction yields nothing, otherwise renders text → markdown via the shared heuristic and delegates to `MarkdownParser`.
- `src/open_ats/parsers/_heuristic.py` — extracted the text→markdown heading/bullet detector out of `txt_parser.py` so PDF and TXT share one implementation. No behavioural change for TXT.
- `src/open_ats/parsers/__init__.py` — `.pdf` registered; `supported_extensions()` now reports the full FR-1 set: `.docx`, `.markdown`, `.md`, `.pdf`, `.txt`.
- `tests/unit/test_pdf_parser.py` (16 tests) — single-column / multi-column / image-based fixture coverage, FR-1.3 verbatim-message check, NFR-1 partial perf gate (<2s parse), determinism, dispatcher wiring, error paths.
- 3 PDF fixtures: `tests/fixtures/resumes/{single_column,multi_column,image_based}.pdf`, generated via the extended `_build_binary_fixtures.py` (now also produces PDFs).
- `tests/fixtures/_build_binary_fixtures.py` — extended to produce PDF fixtures via fpdf2; includes `_to_helvetica_safe` to substitute em-dash/curly-quotes/bullet for ASCII equivalents (fpdf2's bundled core fonts are WinAnsi-only).
- `pyproject.toml` — `fpdf2>=2.7.0` added to `[dev]` extras (fixture-only dep).

### Changed
- README "Phase 1 (MVP)" status: PDF parsing checked off; FR-1 (resume parsing) is implementation-complete across all four formats.
- `tests/unit/test_markdown_parser.py` and `tests/unit/test_docx_parser.py`: unsupported-extension canary migrated `.pdf` → `.rtf` (`.pdf` now wired).
- `src/open_ats/parsers/txt_parser.py` — refactored to import `text_to_markdown` from `_heuristic.py`; no behavioural change.

### Added (Sprint 2 — DOCX & TXT Parsers)
- `src/open_ats/parsers/docx_parser.py` — `DocxParser` walks the document body in order (paragraphs + tables), classifies each paragraph by Word style (Heading 1-6, List Bullet/Number/Paragraph, body), preserves bold runs as `**markers**` so experience titles split correctly downstream, then delegates to `MarkdownParser`. Tables are rendered cell-by-cell as fallback text and surfaced via `formatting.table_detected` warning.
- `src/open_ats/parsers/txt_parser.py` — `TxtParser` heuristically promotes ALL CAPS lines, "Section:" lines, and underline-decorated lines (`===`/`---`) to markdown headings (only when the heading text classifies into a known `SectionType`), normalizes bullet styles (`-`, `*`, `•`, `1.`), then delegates to `MarkdownParser`.
- `src/open_ats/parsers/__init__.py` — `.docx` and `.txt` registered in dispatcher; `parse_resume("foo.pdf")` still raises `UnsupportedFormatError` (PDF lands Sprint 3).
- `tests/fixtures/_build_binary_fixtures.py` — reproducible script that regenerates DOCX/TXT fixtures from existing markdown originals.
- 6 new fixtures: `tests/fixtures/resumes/{entry_level,mid_level,executive}.{docx,txt}` (generated by the script above; checked into git so CI doesn't need to regenerate).
- `tests/unit/test_docx_parser.py` (16 tests) + `tests/unit/test_txt_parser.py` (16 tests) — full FR-1.2/FR-1.4 coverage including determinism, table-warning, error handling, and dispatcher routing.

### Changed
- README "Phase 1 (MVP)" status: DOCX + TXT parsing now checked off (Sprint 2); PDF still pending (Sprint 3).
- `tests/unit/test_markdown_parser.py::test_unsupported_format_raises` migrated from `.docx` (now wired) to `.pdf` (still unsupported until Sprint 3).

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
