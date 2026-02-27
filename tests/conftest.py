"""Shared test fixtures for aumai-template-verify tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src layout is importable without a full editable install.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest

from aumai_template_verify.models import CheckSeverity, StructureCheck


# ---------------------------------------------------------------------------
# Filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path: Path) -> Path:
    """A completely empty temporary directory — every check should fail."""
    return tmp_path


@pytest.fixture()
def minimal_project(tmp_path: Path) -> Path:
    """Project with only the error-severity required files present."""
    for name in ("README.md", "AGENTS.md", "LICENSE", "pyproject.toml"):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    return tmp_path


@pytest.fixture()
def full_project(tmp_path: Path) -> Path:
    """Project that satisfies every built-in check."""
    # Error-severity files
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("Apache-2.0\n", encoding="utf-8")
    pyproject_content = (
        "[tool.mypy]\nstrict = true\n\n[tool.ruff]\nline-length = 88\n"
    )
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    # Warning-severity files
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
    (tmp_path / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()

    # Info-severity files
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")

    # src layout + py.typed
    pkg_dir = tmp_path / "src" / "mypackage"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "py.typed").touch()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    # .github/workflows
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    return tmp_path


@pytest.fixture()
def custom_checks_yaml(tmp_path: Path) -> Path:
    """A valid YAML file defining two custom checks."""
    content = (
        "checks:\n"
        "  - name: docs_dir_exists\n"
        "    description: docs/ directory must be present\n"
        "    severity: warning\n"
        "    path_pattern: docs\n"
        "  - name: changelog_exists\n"
        "    description: CHANGELOG.md must be present\n"
        "    severity: info\n"
        "    path_pattern: CHANGELOG.md\n"
    )
    yaml_file = tmp_path / "custom_checks.yaml"
    yaml_file.write_text(content, encoding="utf-8")
    return yaml_file


@pytest.fixture()
def invalid_yaml_file(tmp_path: Path) -> Path:
    """A YAML file that is syntactically valid but missing the 'checks' key."""
    yaml_file = tmp_path / "bad_checks.yaml"
    yaml_file.write_text("foo: bar\n", encoding="utf-8")
    return yaml_file


@pytest.fixture()
def malformed_yaml_file(tmp_path: Path) -> Path:
    """A file with invalid YAML syntax."""
    yaml_file = tmp_path / "malformed.yaml"
    yaml_file.write_text("checks: [\nnot closed", encoding="utf-8")
    return yaml_file


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def path_only_check() -> StructureCheck:
    """A StructureCheck that only uses path_pattern."""
    return StructureCheck(
        name="readme_check",
        description="README must exist",
        severity=CheckSeverity.error,
        path_pattern="README.md",
    )


@pytest.fixture()
def content_only_check() -> StructureCheck:
    """A StructureCheck that only uses content_pattern (no path)."""
    return StructureCheck(
        name="content_only",
        description="Requires a content pattern match somewhere",
        severity=CheckSeverity.warning,
        content_pattern=r"strict\s*=\s*true",
    )


@pytest.fixture()
def path_and_content_check() -> StructureCheck:
    """A StructureCheck that uses both path_pattern and content_pattern."""
    return StructureCheck(
        name="mypy_strict",
        description="pyproject.toml must enable mypy strict mode",
        severity=CheckSeverity.warning,
        path_pattern="pyproject.toml",
        content_pattern=r"strict\s*=\s*true",
    )
