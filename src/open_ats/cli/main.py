"""CLI entry point.

Sprint 5 wires the first end-to-end pipeline:

    parse_resume → parse_job_description
                 → KeywordAnalyzer
                 → ScoringEngine
                 → JSON report

Sprint 6+ extends the analyzer pipeline; Sprint 8 introduces
configurable role-level weights; Sprint 9 adds the HTML reporter;
Sprint 10 adds ``compare`` and ``batch`` subcommands.
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click

import open_ats
from open_ats.analyzers.keyword import KeywordAnalyzer
from open_ats.models import ScanResult
from open_ats.parsers import (
    ResumeParseError,
    UnsupportedFormatError,
    parse_resume,
)
from open_ats.parsers.jd_parser import parse_job_description
from open_ats.reporting.json_report import write_json
from open_ats.scoring.engine import ScoringEngine, keyword_only_config


@click.group()
@click.version_option(package_name="open-ats-scanner")
def cli() -> None:
    """Open ATS Resume Scanner."""


@cli.command()
@click.option(
    "--resume",
    "resume_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Resume file (.md, .markdown, .docx, .pdf, .txt).",
)
@click.option(
    "--job-description",
    "jd_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Job description file (.txt or .md).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output report path. Sprint 5 supports .json only.",
)
def scan(resume_path: Path, jd_path: Path, output_path: Path) -> None:
    """Scan a resume against a job description."""
    if output_path.suffix.lower() != ".json":
        raise click.ClickException(
            "Sprint 5 only supports .json output (HTML reporter lands Sprint 9)."
        )

    try:
        resume = parse_resume(resume_path)
    except UnsupportedFormatError as exc:
        raise click.ClickException(str(exc)) from exc
    except ResumeParseError as exc:
        raise click.ClickException(f"Resume parse failed: {exc}") from exc

    try:
        jd = parse_job_description(jd_path)
    except ResumeParseError as exc:
        raise click.ClickException(f"Job description parse failed: {exc}") from exc

    analyzer = KeywordAnalyzer()
    keyword_result = analyzer.analyze(resume, jd)

    config = keyword_only_config()
    score = ScoringEngine().score([keyword_result], config)

    scan_result = ScanResult(
        scan_id=_deterministic_scan_id(resume_path, jd_path),
        timestamp=_deterministic_timestamp(resume_path, jd_path),
        open_ats_version=open_ats.__version__,
        resume_hash=_sha256(resume_path),
        jd_hash=_sha256(jd_path),
        resume=resume,
        job_description=jd,
        analyzer_results=[keyword_result],
        score=score,
        config=config,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(scan_result, output_path)
    click.echo(
        f"Scanned {resume_path.name} against {jd_path.name}: "
        f"score = {score.overall} ({score.rating.value}). "
        f"Wrote {output_path}."
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _deterministic_scan_id(resume_path: Path, jd_path: Path) -> str:
    """A UUIDv5 derived from the input bytes — same inputs → same ID.

    This keeps the JSON report bit-stable across reruns (NFR for
    determinism / FR-9 audit-trail idempotency).
    """
    seed = _sha256(resume_path) + _sha256(jd_path) + open_ats.__version__
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _deterministic_timestamp(resume_path: Path, jd_path: Path) -> datetime:
    """Derive a stable timestamp from the inputs.

    Sprint 5's E2E gate requires byte-identical JSON across two
    successive runs. ``datetime.utcnow()`` would break that. We hash
    the inputs into a 64-bit unsigned integer, then map it into a
    deterministic UTC datetime in 1970–2099. Sprint 10's audit trail
    will record the *real* wall-clock when scans land in SQLite.
    """
    seed = (_sha256(resume_path) + _sha256(jd_path)).encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    # 8 bytes → unsigned 64-bit int → seconds in [0, ~4.3B)
    seconds = int.from_bytes(digest[:8], "big") % (60 * 60 * 24 * 365 * 130)
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def main() -> None:
    """Console-script entrypoint."""
    cli(prog_name="open-ats")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
