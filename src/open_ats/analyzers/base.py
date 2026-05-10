"""Analyzer protocol and shared exception types.

Each analyzer (keyword, quantification, formatting, content quality)
implements the :class:`Analyzer` protocol — `analyze(resume, jd)` →
`AnalyzerResult`. Helpers in this module are shared across analyzers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from open_ats.models import AnalyzerResult, JobDescription, Resume


class AnalyzerError(Exception):
    """Raised when an analyzer cannot run (e.g., bad config, missing database)."""


@runtime_checkable
class Analyzer(Protocol):
    """Common interface every analyzer implements."""

    name: str

    def analyze(self, resume: Resume, jd: JobDescription) -> AnalyzerResult:
        """Score the resume against the job description.

        Returns a populated :class:`AnalyzerResult` whose
        ``score`` is in [0, 100] and whose ``analyzer`` field
        matches this analyzer's ``name``.

        Raises:
            AnalyzerError: configuration or input issue.
        """
        ...


__all__ = ["Analyzer", "AnalyzerError"]
