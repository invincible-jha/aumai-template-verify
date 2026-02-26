"""Core logic for aumai-template-verify: built-in checks and verification engine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import yaml

from aumai_template_verify.models import (
    CheckResult,
    CheckSeverity,
    StructureCheck,
    VerificationReport,
)

# ---------------------------------------------------------------------------
# Built-in check definitions
# ---------------------------------------------------------------------------

_BUILTIN_CHECKS: Final[list[StructureCheck]] = [
    StructureCheck(
        name="readme_exists",
        description="README.md must be present at the project root.",
        severity=CheckSeverity.error,
        path_pattern="README.md",
    ),
    StructureCheck(
        name="contributing_exists",
        description="CONTRIBUTING.md must be present.",
        severity=CheckSeverity.warning,
        path_pattern="CONTRIBUTING.md",
    ),
    StructureCheck(
        name="security_exists",
        description="SECURITY.md must be present.",
        severity=CheckSeverity.warning,
        path_pattern="SECURITY.md",
    ),
    StructureCheck(
        name="agents_md_exists",
        description="AGENTS.md must be present for agent capability documentation.",
        severity=CheckSeverity.error,
        path_pattern="AGENTS.md",
    ),
    StructureCheck(
        name="license_exists",
        description="A LICENSE file must be present.",
        severity=CheckSeverity.error,
        path_pattern="LICENSE",
    ),
    StructureCheck(
        name="pyproject_exists",
        description="pyproject.toml must be present for Python packaging.",
        severity=CheckSeverity.error,
        path_pattern="pyproject.toml",
    ),
    StructureCheck(
        name="src_directory_exists",
        description="A src/ directory must be present (src layout).",
        severity=CheckSeverity.error,
        path_pattern="src",
    ),
    StructureCheck(
        name="tests_directory_exists",
        description="A tests/ directory must be present.",
        severity=CheckSeverity.warning,
        path_pattern="tests",
    ),
    StructureCheck(
        name="github_workflows_exists",
        description=".github/workflows/ directory must be present for CI.",
        severity=CheckSeverity.warning,
        path_pattern=".github/workflows",
    ),
    StructureCheck(
        name="py_typed_marker_exists",
        description="A py.typed marker file must exist inside the package (PEP 561).",
        severity=CheckSeverity.info,
        path_pattern="src/**/py.typed",
    ),
    StructureCheck(
        name="pyproject_has_mypy_strict",
        description="pyproject.toml should enable mypy strict mode.",
        severity=CheckSeverity.warning,
        path_pattern="pyproject.toml",
        content_pattern=r"strict\s*=\s*true",
    ),
    StructureCheck(
        name="pyproject_has_ruff",
        description="pyproject.toml should configure ruff for linting.",
        severity=CheckSeverity.info,
        path_pattern="pyproject.toml",
        content_pattern=r"\[tool\.ruff\]",
    ),
    StructureCheck(
        name="pre_commit_config_exists",
        description=".pre-commit-config.yaml should be present for code quality hooks.",
        severity=CheckSeverity.info,
        path_pattern=".pre-commit-config.yaml",
    ),
]


def _check_path_exists(project_root: Path, pattern: str) -> tuple[bool, str]:
    """Return (passed, message) for a path_pattern check."""
    # Use glob for wildcard patterns, direct stat otherwise.
    if "*" in pattern or "?" in pattern:
        matches = list(project_root.glob(pattern))
        if matches:
            return True, f"Found: {matches[0].relative_to(project_root)}"
        return False, f"No files matching '{pattern}' found."

    target = project_root / pattern
    if target.exists():
        return True, f"Found: {pattern}"
    return False, f"Not found: {pattern}"


def _check_content(project_root: Path, path_pattern: str, content_regex: str) -> tuple[bool, str]:
    """Return (passed, message) for a combined path+content check."""
    if "*" in path_pattern or "?" in path_pattern:
        candidates = list(project_root.glob(path_pattern))
    else:
        candidate = project_root / path_pattern
        candidates = [candidate] if candidate.is_file() else []

    if not candidates:
        return False, f"File not found: {path_pattern}"

    compiled = re.compile(content_regex, re.IGNORECASE | re.MULTILINE)
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if compiled.search(text):
            return True, f"Pattern found in {candidate.relative_to(project_root)}"

    return False, f"Pattern '{content_regex}' not found in {path_pattern}"


class TemplateVerifier:
    """Verify a project directory against AumAI best-practice checks.

    Args:
        extra_checks: Additional :class:`StructureCheck` instances to run
                      alongside the built-in set.
    """

    def __init__(self, extra_checks: list[StructureCheck] | None = None) -> None:
        self._checks: list[StructureCheck] = list(_BUILTIN_CHECKS)
        if extra_checks:
            self._checks.extend(extra_checks)

    def verify(self, project_path: str) -> VerificationReport:
        """Run all checks against *project_path* and return a report.

        Args:
            project_path: Absolute or relative path to the project root.

        Returns:
            A :class:`VerificationReport` with per-check results and an
            aggregate score.
        """
        root = Path(project_path).resolve()
        results: list[CheckResult] = []

        for check in self._checks:
            result = self._apply_check(root, check)
            results.append(result)

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        score = (passed_count / total * 100.0) if total > 0 else 0.0

        # Overall pass: no error-severity failures.
        all_errors_pass = all(
            r.passed
            for r in results
            if r.check.severity == CheckSeverity.error
        )

        return VerificationReport(
            project_path=str(root),
            results=results,
            score=round(score, 1),
            passed=all_errors_pass,
        )

    def _apply_check(self, root: Path, check: StructureCheck) -> CheckResult:
        """Apply a single check to *root* and return a CheckResult."""
        try:
            if check.path_pattern and check.content_pattern:
                passed, message = _check_content(root, check.path_pattern, check.content_pattern)
            elif check.path_pattern:
                passed, message = _check_path_exists(root, check.path_pattern)
            else:
                # content_pattern only — not typical but handle gracefully.
                passed, message = False, "No path_pattern specified; cannot evaluate."
        except Exception as exc:
            passed = False
            message = f"Check raised an exception: {exc}"

        return CheckResult(check=check, passed=passed, message=message)


class CustomCheckLoader:
    """Load additional :class:`StructureCheck` instances from a YAML config."""

    def load(self, config_path: str) -> list[StructureCheck]:
        """Parse *config_path* (YAML) and return a list of StructureChecks.

        Expected YAML format::

            checks:
              - name: custom_check
                description: "My custom check"
                severity: warning
                path_pattern: "docs/"

        Args:
            config_path: Path to the YAML config file.

        Returns:
            A list of :class:`StructureCheck` instances.

        Raises:
            ValueError: When the YAML is structurally invalid.
        """
        text = Path(config_path).read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "checks" not in data:
            raise ValueError(
                "Custom check config must be a YAML mapping with a 'checks' key."
            )
        raw_checks: list[dict[str, object]] = data["checks"]
        return [StructureCheck.model_validate(c) for c in raw_checks]


__all__ = [
    "TemplateVerifier",
    "CustomCheckLoader",
]
