"""CLI entry point. Implementations land in Sprint 5+."""

from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="open-ats-scanner")
def cli() -> None:
    """Open ATS Resume Scanner."""


@cli.command()
def scan() -> None:
    """Scan a resume against a job description.

    Implementation lands in Sprint 5 (first end-to-end slice).
    """
    raise click.ClickException("scan command not yet implemented (Sprint 5)")


if __name__ == "__main__":
    cli()
