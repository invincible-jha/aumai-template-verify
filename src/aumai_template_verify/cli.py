"""CLI entry point for aumai-template-verify."""

from __future__ import annotations

import sys

import click

from aumai_template_verify.core import CustomCheckLoader, TemplateVerifier
from aumai_template_verify.models import CheckResult, CheckSeverity, StructureCheck


_SEVERITY_COLOURS: dict[str, str] = {
    "error": "red",
    "warning": "yellow",
    "info": "blue",
}

_PASS_ICON = click.style("PASS", fg="green", bold=True)
_FAIL_ICON = click.style("FAIL", fg="red", bold=True)


def _print_result(result: CheckResult) -> None:
    """Print a single check result line."""
    icon = _PASS_ICON if result.passed else _FAIL_ICON
    sev_colour = _SEVERITY_COLOURS.get(result.check.severity.value, "white")
    severity_label = click.style(f"[{result.check.severity.value}]", fg=sev_colour)
    click.echo(f"  {icon}  {severity_label}  {result.check.name} — {result.message}")


@click.group()
@click.version_option()
def main() -> None:
    """AumAI TemplateVerify CLI — check project structure against best practices."""


@main.command("check")
@click.argument("project_path", metavar="PROJECT_PATH", type=click.Path())
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with code 1 when any warning-severity check fails (in addition to errors).",
)
@click.option(
    "--custom-checks",
    default=None,
    type=click.Path(exists=True),
    help="Path to a YAML file with additional custom checks.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Only show failing checks.",
)
def check_command(
    project_path: str,
    strict: bool,
    custom_checks: str | None,
    quiet: bool,
) -> None:
    """Verify PROJECT_PATH against AumAI template best practices.

    Exits with code 1 when error-severity checks fail, or when --strict is
    set and warning-severity checks also fail.
    """
    extra: list[StructureCheck] = []
    if custom_checks:
        loader = CustomCheckLoader()
        try:
            extra = loader.load(custom_checks)
        except Exception as exc:
            click.echo(f"Failed to load custom checks: {exc}", err=True)
            sys.exit(1)

    verifier = TemplateVerifier(extra_checks=extra if extra else None)

    try:
        report = verifier.verify(project_path)
    except Exception as exc:
        click.echo(f"Verification error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\nProject: {report.project_path}")
    click.echo(f"Checks run: {len(report.results)}  |  Score: {report.score:.1f}%\n")

    for result in report.results:
        if quiet and result.passed:
            continue
        _print_result(result)

    click.echo("")

    error_failures = [
        r for r in report.results
        if not r.passed and r.check.severity == CheckSeverity.error
    ]
    warning_failures = [
        r for r in report.results
        if not r.passed and r.check.severity == CheckSeverity.warning
    ]

    if error_failures:
        click.echo(
            click.style(
                f"FAILED — {len(error_failures)} error(s), "
                f"{len(warning_failures)} warning(s).",
                fg="red",
                bold=True,
            )
        )
        sys.exit(1)
    elif strict and warning_failures:
        click.echo(
            click.style(
                f"FAILED (strict) — 0 errors, {len(warning_failures)} warning(s).",
                fg="yellow",
                bold=True,
            )
        )
        sys.exit(1)
    else:
        suffix = f" ({len(warning_failures)} warning(s))" if warning_failures else ""
        click.echo(click.style(f"PASSED{suffix}", fg="green", bold=True))


if __name__ == "__main__":
    main()
