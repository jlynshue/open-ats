# Contributing to Open ATS

Thank you for your interest in contributing to Open ATS! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, constructive, and professional. We're building tools to help job seekers, so let's maintain a supportive community.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Resume format (Markdown, DOCX, PDF)
   - Job description sample (if applicable)
   - Expected vs. actual behavior
   - Error messages and logs
   - Python version and OS

### Suggesting Features

1. Check existing feature requests
2. Use the feature request template
3. Explain:
   - The problem you're solving
   - Your proposed solution
   - Why this benefits users
   - Implementation complexity estimate

### Contributing Code

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/jlynshue/open-ats.git
cd open-ats

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Development Workflow

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes:**
   - Follow code style guidelines (Black, Ruff)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests:**
   ```bash
   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=term-missing

   # Run specific test file
   pytest tests/unit/test_parsers.py

   # Run only fast tests (skip slow ones)
   pytest -m "not slow"
   ```

4. **Format and lint:**
   ```bash
   # Format code
   black src/ tests/

   # Lint
   ruff check src/ tests/

   # Type check
   mypy src/
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add PDF parsing support"
   # or
   git commit -m "fix: correct quantification rate calculation"
   ```

   **Commit message format:**
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test additions or changes
   - `refactor:` Code refactoring
   - `perf:` Performance improvements
   - `chore:` Build/tool changes

6. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

#### Code Style

- **Python:** Follow PEP 8 (enforced by Black and Ruff)
- **Line length:** 88 characters (Black default)
- **Type hints:** Required for all functions
- **Docstrings:** Required for public functions (Google style)

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

#### Testing Guidelines

- **Coverage target:** 80%+ for new code
- **Test all edge cases:** Empty inputs, malformed data, large files
- **Use fixtures:** Store test data in `tests/fixtures/`
- **Mark slow tests:** Use `@pytest.mark.slow` for tests >1 second
- **Mock external dependencies:** Don't make real API calls in tests

Example:
```python
import pytest
from open_ats.parsers import parse_resume

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

### Contributing Keyword Databases

We need community help building industry-specific keyword databases!

**Format:** `keyword_databases/{industry}_keywords.yaml`

Example:
```yaml
# keyword_databases/data_science_keywords.yaml
hard_skills:
  - Python
  - R
  - SQL
  - TensorFlow
  - PyTorch
  - Pandas
  - NumPy
  - Scikit-learn

soft_skills:
  - Data storytelling
  - Statistical thinking
  - Problem solving
  - Communication

industry_terms:
  - Machine learning
  - Deep learning
  - Feature engineering
  - Model deployment
  - A/B testing
```

### Contributing Documentation

- Fix typos and unclear explanations
- Add examples and use cases
- Improve API documentation
- Create tutorials and guides

### Contributing Test Data

We need diverse test resumes and job descriptions!

**Requirements:**
- Anonymize all PII (names, emails, phone numbers)
- Include variety: entry-level, mid-level, senior, executive
- Various industries: tech, finance, healthcare, etc.
- Different formats: Markdown, DOCX, PDF

**Contribution process:**
1. Anonymize the data
2. Add to `tests/fixtures/`
3. Document expected parsing results
4. Create test cases using the fixture

## Pull Request Process

1. **PR checklist:**
   - [ ] Tests pass (`pytest`)
   - [ ] Code formatted (`black`)
   - [ ] Linting passes (`ruff`)
   - [ ] Type checking passes (`mypy`)
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   - [ ] All conversations resolved

2. **PR title format:**
   ```
   feat: add semantic keyword matching
   fix: correct PDF parsing for multi-column layouts
   docs: improve scoring system documentation
   ```

3. **PR description should include:**
   - What problem does this solve?
   - What changes were made?
   - How was it tested?
   - Any breaking changes?
   - Related issues (if any)

4. **Review process:**
   - At least one maintainer approval required
   - All CI checks must pass
   - Address all review comments

## Areas Needing Contribution

### High Priority

1. **Keyword database expansion**
   - Industry-specific terms (finance, healthcare, legal, etc.)
   - International keywords (UK spelling variants, etc.)
   - Emerging tech terms (AI/ML, blockchain, etc.)

2. **Resume parsing edge cases**
   - Complex PDF layouts
   - Unusual formatting
   - Non-English resumes

3. **Scoring validation**
   - Parallel testing against commercial tools
   - Statistical analysis of correlation
   - Weight optimization

4. **Documentation**
   - User guides and tutorials
   - Video walkthroughs
   - API documentation examples

### Medium Priority

5. **Test coverage expansion**
   - Integration tests
   - Performance benchmarks
   - Security tests

6. **Performance optimization**
   - PDF parsing speed
   - NLP pipeline efficiency
   - Memory usage reduction

7. **UI/UX improvements**
   - CLI user experience
   - Error message clarity
   - Report visualization

### Future Features

8. **Advanced NLP**
   - Semantic matching
   - Synonym detection
   - Context-aware keyword extraction

9. **Web interface**
   - Frontend development (React/Vue)
   - API design
   - User authentication

10. **Integrations**
    - Resume builder plugins
    - Job board connections
    - ATS vendor APIs

## Questions?

- Open a [Discussion](https://github.com/jlynshue/open-ats/discussions) for questions
- Join our [Discord](https://discord.gg/[PLACEHOLDER]) for real-time chat
- Check existing [Issues](https://github.com/jlynshue/open-ats/issues) and [PRs](https://github.com/jlynshue/open-ats/pulls)

## Recognition

Contributors will be recognized in:
- README.md Contributors section
- Release notes
- Project website (coming soon)

Thank you for helping make job searching more transparent and accessible!
