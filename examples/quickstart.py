"""Quickstart examples for aumai-template-verify.

Run this file directly to see the verifier in action:

    python examples/quickstart.py

Each demo function is self-contained and demonstrates a distinct feature.
The demos create temporary directories so they run reliably regardless of
the state of your working directory.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from aumai_template_verify import (
    CheckSeverity,
    CustomCheckLoader,
    StructureCheck,
    TemplateVerifier,
)


# ---------------------------------------------------------------------------
# Demo 1: Basic verification — a well-structured project
# ---------------------------------------------------------------------------

def demo_passing_project() -> None:
    """Verify a project that satisfies all error-severity checks."""
    print("\n--- Demo 1: Passing Project ---")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create the files that the error-severity checks require
        (root / "README.md").write_text("# My Agent\n")
        (root / "AGENTS.md").write_text("# Agent Capabilities\n")
        (root / "LICENSE").write_text("Apache License, Version 2.0\n")
        (root / "pyproject.toml").write_text("[project]\nname = 'my-agent'\n")
        (root / "src").mkdir()

        verifier = TemplateVerifier()
        report = verifier.verify(str(root))

        print(f"  Score: {report.score:.1f}%")
        print(f"  Passed: {report.passed}")
        print(f"  Errors: {report.error_count}, Warnings: {report.warning_count}")

        # Show failing checks (there will be some warnings/info missing)
        for result in report.failed_results:
            print(f"  FAIL [{result.check.severity.value}] {result.check.name}")


# ---------------------------------------------------------------------------
# Demo 2: Failing project — missing required files
# ---------------------------------------------------------------------------

def demo_failing_project() -> None:
    """Verify a project that is missing error-severity required files."""
    print("\n--- Demo 2: Failing Project ---")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Only create README — missing LICENSE, AGENTS.md, pyproject.toml, src/
        (root / "README.md").write_text("# Incomplete Project\n")

        verifier = TemplateVerifier()
        report = verifier.verify(str(root))

        print(f"  Score: {report.score:.1f}%")
        print(f"  Passed: {report.passed}")
        print(f"  Error failures: {report.error_count}")

        # List all the blocking failures
        error_failures = [
            r for r in report.failed_results
            if r.check.severity == CheckSeverity.error
        ]
        for result in error_failures:
            print(f"  Missing: {result.check.name} — {result.message}")


# ---------------------------------------------------------------------------
# Demo 3: Content check — verify a file contains a required pattern
# ---------------------------------------------------------------------------

def demo_content_check() -> None:
    """Show how content_pattern checks work: verify text inside files."""
    print("\n--- Demo 3: Content Pattern Check ---")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create a pyproject.toml WITH mypy strict enabled
        pyproject_with_strict = """
[project]
name = "my-agent"

[tool.mypy]
strict = true

[tool.ruff]
line-length = 100
"""
        (root / "pyproject.toml").write_text(pyproject_with_strict)

        # Add other required files so we get a clean picture
        (root / "README.md").write_text("# My Agent\n")
        (root / "AGENTS.md").write_text("# Agent Capabilities\n")
        (root / "LICENSE").write_text("Apache License\n")
        (root / "src").mkdir()

        verifier = TemplateVerifier()
        report = verifier.verify(str(root))

        # Show just the mypy and ruff checks
        for result in report.results:
            if result.check.name in ("pyproject_has_mypy_strict", "pyproject_has_ruff"):
                status = "PASS" if result.passed else "FAIL"
                print(f"  {status} {result.check.name}: {result.message}")


# ---------------------------------------------------------------------------
# Demo 4: Custom checks from a programmatic StructureCheck
# ---------------------------------------------------------------------------

def demo_custom_checks() -> None:
    """Show how to add custom checks beyond the built-in set."""
    print("\n--- Demo 4: Custom Checks ---")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create standard files
        (root / "README.md").write_text("# My Agent\n")
        (root / "AGENTS.md").write_text("# Capabilities\n")
        (root / "LICENSE").write_text("Apache License\n")
        (root / "pyproject.toml").write_text("[project]\nname='x'\n")
        (root / "src").mkdir()

        # Also create a CHANGELOG — this is what our custom check requires
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## v0.1.0\n- Initial release\n")

        custom_checks = [
            StructureCheck(
                name="changelog_exists",
                description="CHANGELOG.md must track releases.",
                severity=CheckSeverity.warning,
                path_pattern="CHANGELOG.md",
            ),
            StructureCheck(
                name="docs_dir_exists",
                description="A docs/ directory must be present.",
                severity=CheckSeverity.info,
                path_pattern="docs",
            ),
        ]

        verifier = TemplateVerifier(extra_checks=custom_checks)
        report = verifier.verify(str(root))

        # Show only our custom checks
        custom_names = {c.name for c in custom_checks}
        for result in report.results:
            if result.check.name in custom_names:
                status = "PASS" if result.passed else "FAIL"
                print(f"  {status} [{result.check.severity.value}] {result.check.name}: {result.message}")


# ---------------------------------------------------------------------------
# Demo 5: CustomCheckLoader — load checks from a YAML file
# ---------------------------------------------------------------------------

def demo_custom_check_loader() -> None:
    """Show CustomCheckLoader: load additional checks from a YAML config file."""
    print("\n--- Demo 5: CustomCheckLoader ---")

    yaml_content = """
checks:
  - name: contributing_has_content
    description: "CONTRIBUTING.md must not be empty."
    severity: warning
    path_pattern: "CONTRIBUTING.md"
    content_pattern: "\\\\w+"

  - name: examples_dir_exists
    description: "An examples/ directory must be present."
    severity: info
    path_pattern: "examples"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Write a YAML config file
        config_file = root / "custom-checks.yaml"
        config_file.write_text(yaml_content)

        # Create a minimal project
        (root / "README.md").write_text("# My Agent\n")
        (root / "AGENTS.md").write_text("# Capabilities\n")
        (root / "LICENSE").write_text("Apache License\n")
        (root / "pyproject.toml").write_text("[project]\nname='x'\n")
        (root / "src").mkdir()
        (root / "CONTRIBUTING.md").write_text("# How to contribute\n\nPlease read this guide.\n")
        (root / "examples").mkdir()

        # Load and use the custom checks
        loader = CustomCheckLoader()
        extra = loader.load(str(config_file))
        print(f"  Loaded {len(extra)} custom check(s) from YAML")

        verifier = TemplateVerifier(extra_checks=extra)
        report = verifier.verify(str(root))

        # Show results for the custom checks
        custom_names = {c.name for c in extra}
        for result in report.results:
            if result.check.name in custom_names:
                status = "PASS" if result.passed else "FAIL"
                print(f"  {status} {result.check.name}: {result.message}")


# ---------------------------------------------------------------------------
# Main: run all demos
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all quickstart demos in sequence."""
    print("=" * 60)
    print("aumai-template-verify quickstart demos")
    print("=" * 60)

    demo_passing_project()
    demo_failing_project()
    demo_content_check()
    demo_custom_checks()
    demo_custom_check_loader()

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
