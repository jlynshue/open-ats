"""Shared pytest fixtures for the open-ats test suite.

Sprint 0 ships only the path helpers — concrete fixtures land alongside
the parsers/analyzers that consume them (Sprint 1+).
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESUMES_DIR = FIXTURES_DIR / "resumes"
JOB_DESCRIPTIONS_DIR = FIXTURES_DIR / "job_descriptions"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Absolute path to tests/fixtures/."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def resumes_dir() -> Path:
    """Absolute path to tests/fixtures/resumes/."""
    return RESUMES_DIR


@pytest.fixture(scope="session")
def job_descriptions_dir() -> Path:
    """Absolute path to tests/fixtures/job_descriptions/."""
    return JOB_DESCRIPTIONS_DIR
