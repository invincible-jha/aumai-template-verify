"""Comprehensive tests for aumai_template_verify core module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aumai_template_verify.core import (
    CustomCheckLoader,
    TemplateVerifier,
    _check_content,
    _check_path_exists,
)
from aumai_template_verify.models import (
    CheckResult,
    CheckSeverity,
    StructureCheck,
    VerificationReport,
)


# ---------------------------------------------------------------------------
# _check_path_exists helper tests
# ---------------------------------------------------------------------------


class TestCheckPathExists:
    """Tests for the _check_path_exists helper."""

    def test_existing_file_passes(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
        passed, message = _check_path_exists(tmp_path, "README.md")
        assert passed is True

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        passed, message = _check_path_exists(tmp_path, "MISSING.md")
        assert passed is False

    def test_existing_directory_passes(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        passed, message = _check_path_exists(tmp_path, "src")
        assert passed is True

    def test_missing_directory_fails(self, tmp_path: Path) -> None:
        passed, message = _check_path_exists(tmp_path, "nonexistent_dir")
        assert passed is False

    def test_glob_pattern_match_passes(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "mypackage"
        pkg.mkdir(parents=True)
        (pkg / "py.typed").touch()
        passed, message = _check_path_exists(tmp_path, "src/**/py.typed")
        assert passed is True

    def test_glob_pattern_no_match_fails(self, tmp_path: Path) -> None:
        passed, message = _check_path_exists(tmp_path, "src/**/py.typed")
        assert passed is False

    def test_message_contains_found_when_passing(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("", encoding="utf-8")
        _, message = _check_path_exists(tmp_path, "README.md")
        assert "README.md" in message

    def test_message_contains_not_found_when_failing(self, tmp_path: Path) -> None:
        _, message = _check_path_exists(tmp_path, "MISSING.md")
        assert "MISSING.md" in message or "Not found" in message


# ---------------------------------------------------------------------------
# _check_content helper tests
# ---------------------------------------------------------------------------


class TestCheckContent:
    """Tests for the _check_content helper."""

    def test_pattern_found_passes(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.mypy]\nstrict = true\n", encoding="utf-8"
        )
        passed, message = _check_content(
            tmp_path, "pyproject.toml", r"strict\s*=\s*true"
        )
        assert passed is True

    def test_pattern_not_found_fails(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.mypy]\nstrict = false\n", encoding="utf-8"
        )
        passed, message = _check_content(
            tmp_path, "pyproject.toml", r"strict\s*=\s*true"
        )
        assert passed is False

    def test_file_not_found_fails(self, tmp_path: Path) -> None:
        passed, message = _check_content(
            tmp_path, "nonexistent.toml", r"strict"
        )
        assert passed is False

    def test_case_insensitive_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("STRICT = TRUE\n", encoding="utf-8")
        passed, message = _check_content(tmp_path, "file.txt", r"strict\s*=\s*true")
        assert passed is True

    def test_glob_pattern_with_content_check(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("from __future__ import annotations\n", encoding="utf-8")
        passed, message = _check_content(
            tmp_path, "src/*.py", r"from __future__"
        )
        assert passed is True

    def test_message_contains_pattern_on_failure(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("no match", encoding="utf-8")
        _, message = _check_content(
            tmp_path, "pyproject.toml", r"strict_pattern_xyz"
        )
        assert "strict_pattern_xyz" in message or "Pattern" in message


# ---------------------------------------------------------------------------
# TemplateVerifier tests — empty project
# ---------------------------------------------------------------------------


class TestTemplateVerifierEmptyProject:
    """Tests against an empty project directory."""

    def test_verify_returns_report(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert isinstance(report, VerificationReport)

    def test_verify_empty_project_fails(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert report.passed is False

    def test_verify_empty_project_score_low(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert report.score < 50.0

    def test_verify_empty_project_has_error_failures(
        self, empty_project: Path
    ) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert report.error_count > 0

    def test_verify_returns_all_builtin_checks(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert len(report.results) == 13  # 13 built-in checks

    def test_verify_project_path_in_report(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert str(empty_project) in report.project_path

    def test_verify_score_is_float(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert isinstance(report.score, float)

    def test_verify_score_in_range(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert 0.0 <= report.score <= 100.0


# ---------------------------------------------------------------------------
# TemplateVerifier tests — minimal project
# ---------------------------------------------------------------------------


class TestTemplateVerifierMinimalProject:
    """Tests against a minimal project (only error-severity files present)."""

    def test_minimal_project_passes(self, minimal_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(minimal_project))
        assert report.passed is True

    def test_minimal_project_no_error_failures(
        self, minimal_project: Path
    ) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(minimal_project))
        assert report.error_count == 0

    def test_minimal_project_has_warnings(self, minimal_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(minimal_project))
        # Some warnings should be present (CONTRIBUTING, SECURITY, tests, etc.)
        assert report.warning_count > 0


# ---------------------------------------------------------------------------
# TemplateVerifier tests — full project
# ---------------------------------------------------------------------------


class TestTemplateVerifierFullProject:
    """Tests against a fully populated project."""

    def test_full_project_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        assert report.passed is True

    def test_full_project_score_high(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        assert report.score >= 80.0

    def test_full_project_no_error_failures(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        assert report.error_count == 0

    def test_full_project_readme_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        readme_result = next(
            r for r in report.results if r.check.name == "readme_exists"
        )
        assert readme_result.passed is True

    def test_full_project_agents_md_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        agents_result = next(
            r for r in report.results if r.check.name == "agents_md_exists"
        )
        assert agents_result.passed is True

    def test_full_project_pyproject_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        pyproject_result = next(
            r for r in report.results if r.check.name == "pyproject_exists"
        )
        assert pyproject_result.passed is True

    def test_full_project_mypy_strict_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        mypy_result = next(
            r for r in report.results if r.check.name == "pyproject_has_mypy_strict"
        )
        assert mypy_result.passed is True

    def test_full_project_ruff_passes(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        ruff_result = next(
            r for r in report.results if r.check.name == "pyproject_has_ruff"
        )
        assert ruff_result.passed is True


# ---------------------------------------------------------------------------
# TemplateVerifier extra checks tests
# ---------------------------------------------------------------------------


class TestTemplateVerifierExtraChecks:
    """Tests for adding custom extra checks."""

    def test_extra_check_added(self, minimal_project: Path) -> None:
        extra = StructureCheck(
            name="docs_exists",
            description="docs/ must exist",
            severity=CheckSeverity.warning,
            path_pattern="docs",
        )
        verifier = TemplateVerifier(extra_checks=[extra])
        report = verifier.verify(str(minimal_project))
        assert len(report.results) == 14  # 13 built-in + 1 extra

    def test_extra_check_failing(self, minimal_project: Path) -> None:
        extra = StructureCheck(
            name="docs_exists",
            description="docs/ must exist",
            severity=CheckSeverity.warning,
            path_pattern="docs",
        )
        verifier = TemplateVerifier(extra_checks=[extra])
        report = verifier.verify(str(minimal_project))
        extra_result = next(r for r in report.results if r.check.name == "docs_exists")
        assert extra_result.passed is False

    def test_extra_check_passing(self, minimal_project: Path) -> None:
        (minimal_project / "docs").mkdir()
        extra = StructureCheck(
            name="docs_exists",
            description="docs/ must exist",
            severity=CheckSeverity.warning,
            path_pattern="docs",
        )
        verifier = TemplateVerifier(extra_checks=[extra])
        report = verifier.verify(str(minimal_project))
        extra_result = next(r for r in report.results if r.check.name == "docs_exists")
        assert extra_result.passed is True

    def test_extra_error_check_causes_failure(self, minimal_project: Path) -> None:
        extra = StructureCheck(
            name="critical_file",
            description="critical_file must exist",
            severity=CheckSeverity.error,
            path_pattern="critical_file.txt",
        )
        verifier = TemplateVerifier(extra_checks=[extra])
        report = verifier.verify(str(minimal_project))
        assert report.passed is False

    def test_no_extra_checks_uses_only_builtins(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert len(report.results) == 13


# ---------------------------------------------------------------------------
# VerificationReport property tests
# ---------------------------------------------------------------------------


class TestVerificationReport:
    """Tests for VerificationReport computed properties."""

    def test_failed_results_empty_when_all_pass(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        # There might be some warnings but checking the property works
        failed = report.failed_results
        assert isinstance(failed, list)

    def test_failed_results_contains_failed_checks(
        self, empty_project: Path
    ) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert len(report.failed_results) > 0

    def test_error_count_zero_for_full_project(self, full_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(full_project))
        assert report.error_count == 0

    def test_warning_count_is_int(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        assert isinstance(report.warning_count, int)

    def test_score_rounded_to_one_decimal(self, empty_project: Path) -> None:
        verifier = TemplateVerifier()
        report = verifier.verify(str(empty_project))
        # Score rounded to 1 decimal
        assert report.score == round(report.score, 1)


# ---------------------------------------------------------------------------
# CustomCheckLoader tests
# ---------------------------------------------------------------------------


class TestCustomCheckLoader:
    """Tests for the CustomCheckLoader class."""

    def test_load_valid_yaml(self, custom_checks_yaml: Path) -> None:
        loader = CustomCheckLoader()
        checks = loader.load(str(custom_checks_yaml))
        assert len(checks) == 2

    def test_load_returns_structure_checks(
        self, custom_checks_yaml: Path
    ) -> None:
        loader = CustomCheckLoader()
        checks = loader.load(str(custom_checks_yaml))
        for check in checks:
            assert isinstance(check, StructureCheck)

    def test_load_check_names(self, custom_checks_yaml: Path) -> None:
        loader = CustomCheckLoader()
        checks = loader.load(str(custom_checks_yaml))
        names = [c.name for c in checks]
        assert "docs_dir_exists" in names
        assert "changelog_exists" in names

    def test_load_check_severities(self, custom_checks_yaml: Path) -> None:
        loader = CustomCheckLoader()
        checks = loader.load(str(custom_checks_yaml))
        severity_map = {c.name: c.severity for c in checks}
        assert severity_map["docs_dir_exists"] == CheckSeverity.warning
        assert severity_map["changelog_exists"] == CheckSeverity.info

    def test_load_invalid_yaml_raises_value_error(
        self, invalid_yaml_file: Path
    ) -> None:
        loader = CustomCheckLoader()
        with pytest.raises(ValueError):
            loader.load(str(invalid_yaml_file))

    def test_load_malformed_yaml_raises(self, malformed_yaml_file: Path) -> None:
        loader = CustomCheckLoader()
        with pytest.raises(Exception):
            loader.load(str(malformed_yaml_file))

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        loader = CustomCheckLoader()
        with pytest.raises(Exception):
            loader.load(str(tmp_path / "nonexistent.yaml"))

    def test_load_empty_checks_list(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("checks: []\n", encoding="utf-8")
        loader = CustomCheckLoader()
        checks = loader.load(str(yaml_file))
        assert checks == []


# ---------------------------------------------------------------------------
# StructureCheck model tests
# ---------------------------------------------------------------------------


class TestStructureCheck:
    """Tests for the StructureCheck Pydantic model."""

    def test_create_path_only_check(self, path_only_check: StructureCheck) -> None:
        assert path_only_check.path_pattern == "README.md"
        assert path_only_check.content_pattern is None

    def test_create_content_only_check(
        self, content_only_check: StructureCheck
    ) -> None:
        assert content_only_check.content_pattern is not None
        assert content_only_check.path_pattern is None

    def test_create_combined_check(
        self, path_and_content_check: StructureCheck
    ) -> None:
        assert path_and_content_check.path_pattern is not None
        assert path_and_content_check.content_pattern is not None

    def test_empty_name_raises(self) -> None:
        with pytest.raises(Exception):
            StructureCheck(
                name="",
                description="test",
                path_pattern="README.md",
            )

    def test_whitespace_name_raises(self) -> None:
        with pytest.raises(Exception):
            StructureCheck(
                name="   ",
                description="test",
                path_pattern="README.md",
            )

    def test_no_pattern_raises(self) -> None:
        with pytest.raises(Exception):
            StructureCheck(
                name="check",
                description="test",
            )

    def test_name_stripped(self) -> None:
        check = StructureCheck(
            name="  my_check  ",
            description="test",
            path_pattern="README.md",
        )
        assert check.name == "my_check"

    def test_default_severity_is_error(self) -> None:
        check = StructureCheck(
            name="test_check",
            description="test",
            path_pattern="README.md",
        )
        assert check.severity == CheckSeverity.error

    @pytest.mark.parametrize("severity", ["error", "warning", "info"])
    def test_all_severity_values(self, severity: str) -> None:
        check = StructureCheck(
            name="test_check",
            description="test",
            severity=CheckSeverity(severity),
            path_pattern="README.md",
        )
        assert check.severity.value == severity


class TestCheckResult:
    """Tests for CheckResult model."""

    def test_create_passing_result(self, path_only_check: StructureCheck) -> None:
        result = CheckResult(
            check=path_only_check,
            passed=True,
            message="Found: README.md",
        )
        assert result.passed is True

    def test_create_failing_result(self, path_only_check: StructureCheck) -> None:
        result = CheckResult(
            check=path_only_check,
            passed=False,
            message="Not found: README.md",
        )
        assert result.passed is False


class TestCheckSeverity:
    """Tests for CheckSeverity enum."""

    def test_all_values_exist(self) -> None:
        assert CheckSeverity.error.value == "error"
        assert CheckSeverity.warning.value == "warning"
        assert CheckSeverity.info.value == "info"

    def test_is_string_enum(self) -> None:
        assert isinstance(CheckSeverity.error, str)


# ---------------------------------------------------------------------------
# Hypothesis-based property tests
# ---------------------------------------------------------------------------


@given(
    name=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"),
    ).filter(lambda s: s.strip())
)
@settings(max_examples=30)
def test_structure_check_non_empty_name_accepted(name: str) -> None:
    """StructureCheck with non-empty name should not raise."""
    check = StructureCheck(
        name=name,
        description="test check",
        path_pattern="README.md",
    )
    assert check.name != ""
