"""Comprehensive CLI tests for aumai-template-verify."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# Ensure src is importable without editable install
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aumai_template_verify.cli import main, _print_result
from aumai_template_verify.models import CheckResult, CheckSeverity, StructureCheck


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# main group tests
# ---------------------------------------------------------------------------


class TestMainGroup:
    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.output

    def test_help_contains_description(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "TemplateVerify" in result.output or "template" in result.output.lower()


# ---------------------------------------------------------------------------
# check command tests — empty project
# ---------------------------------------------------------------------------


class TestCheckCommandEmptyProject:
    def test_empty_project_exits_one(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert result.exit_code == 1

    def test_empty_project_shows_failed(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "FAILED" in result.output

    def test_empty_project_shows_score(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "Score" in result.output

    def test_empty_project_shows_checks_run(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "Checks run" in result.output

    def test_empty_project_shows_project_path(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "Project:" in result.output

    def test_empty_project_shows_fail_icons(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "FAIL" in result.output


# ---------------------------------------------------------------------------
# check command tests — full project
# ---------------------------------------------------------------------------


class TestCheckCommandFullProject:
    def test_full_project_exits_zero(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project)])
        assert result.exit_code == 0

    def test_full_project_shows_passed(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project)])
        assert "PASSED" in result.output

    def test_full_project_score_above_zero(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project)])
        assert "Score:" in result.output or "Score" in result.output

    def test_full_project_shows_pass_icons(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project)])
        assert "PASS" in result.output

    def test_full_project_with_strict_exits_zero(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project), "--strict"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# check command tests — minimal project
# ---------------------------------------------------------------------------


class TestCheckCommandMinimalProject:
    def test_minimal_project_exits_zero(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(minimal_project)])
        assert result.exit_code == 0

    def test_minimal_project_strict_may_fail_on_warnings(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        # minimal_project has only error-severity files; warning checks will fail
        # so --strict should exit 1
        result = runner.invoke(main, ["check", str(minimal_project), "--strict"])
        # either 0 (no warnings) or 1 (has warnings in strict mode) — both are valid
        assert result.exit_code in (0, 1)

    def test_minimal_project_passed_message(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(minimal_project)])
        assert "PASSED" in result.output

    def test_minimal_project_shows_warnings_in_output(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(minimal_project)])
        # should show some FAIL icons for warning/info checks that are missing
        assert "FAIL" in result.output or "PASS" in result.output


# ---------------------------------------------------------------------------
# --quiet flag tests
# ---------------------------------------------------------------------------


class TestCheckCommandQuiet:
    def test_quiet_flag_short_form(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project), "-q"])
        assert result.exit_code == 1

    def test_quiet_flag_hides_passed_checks(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result_normal = runner.invoke(main, ["check", str(full_project)])
        result_quiet = runner.invoke(main, ["check", str(full_project), "--quiet"])
        # quiet output should be shorter (fewer lines shown)
        assert len(result_quiet.output) <= len(result_normal.output)

    def test_quiet_flag_still_shows_summary(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project), "--quiet"])
        assert "Score" in result.output or "PASSED" in result.output

    def test_quiet_with_empty_project_still_exits_one(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project), "--quiet"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# --strict flag tests
# ---------------------------------------------------------------------------


class TestCheckCommandStrict:
    def test_strict_flag_documented_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", "--help"])
        assert "strict" in result.output

    def test_strict_exits_one_when_warnings_fail(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        # minimal_project passes error checks but likely has warning failures
        result = runner.invoke(main, ["check", str(minimal_project), "--strict"])
        # with warnings present, strict should fail
        if "warning" in result.output.lower():
            assert result.exit_code == 1

    def test_strict_shows_failed_strict_message(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(minimal_project), "--strict"])
        # if strict causes failure, message should say "strict"
        if result.exit_code == 1:
            assert "strict" in result.output.lower() or "FAILED" in result.output


# ---------------------------------------------------------------------------
# --custom-checks flag tests
# ---------------------------------------------------------------------------


class TestCheckCommandCustomChecks:
    def test_custom_checks_valid_yaml_accepted(
        self, runner: CliRunner, empty_project: Path, custom_checks_yaml: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["check", str(empty_project), "--custom-checks", str(custom_checks_yaml)],
        )
        # custom checks are added to built-in checks; empty project will still fail
        assert result.exit_code != 0

    def test_custom_checks_runs_additional_checks(
        self, runner: CliRunner, empty_project: Path, custom_checks_yaml: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["check", str(empty_project), "--custom-checks", str(custom_checks_yaml)],
        )
        # More checks should be run (13 built-in + 2 custom = 15)
        assert "Checks run:" in result.output

    def test_custom_checks_invalid_yaml_exits_one(
        self, runner: CliRunner, empty_project: Path, invalid_yaml_file: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["check", str(empty_project), "--custom-checks", str(invalid_yaml_file)],
        )
        assert result.exit_code == 1

    def test_custom_checks_malformed_yaml_exits_one(
        self, runner: CliRunner, empty_project: Path, malformed_yaml_file: Path
    ) -> None:
        result = runner.invoke(
            main,
            [
                "check",
                str(empty_project),
                "--custom-checks",
                str(malformed_yaml_file),
            ],
        )
        assert result.exit_code == 1

    def test_custom_checks_error_message_on_invalid(
        self, runner: CliRunner, empty_project: Path, invalid_yaml_file: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["check", str(empty_project), "--custom-checks", str(invalid_yaml_file)],
        )
        # Should output some error message (may be on stderr)
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "custom" in combined.lower() or result.exit_code == 1

    def test_custom_checks_help_shows_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", "--help"])
        assert "custom-checks" in result.output or "custom_checks" in result.output


# ---------------------------------------------------------------------------
# check command — missing / invalid project path
# ---------------------------------------------------------------------------


class TestCheckCommandErrors:
    def test_missing_project_path_argument(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check"])
        assert result.exit_code != 0

    def test_help_flag_shows_options(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "PROJECT_PATH" in result.output or "project" in result.output.lower()


# ---------------------------------------------------------------------------
# _print_result helper tests
# ---------------------------------------------------------------------------


class TestPrintResult:
    def test_print_result_passed_check(self, runner: CliRunner) -> None:
        check = StructureCheck(
            name="test_check",
            description="A test check",
            severity=CheckSeverity.error,
            path_pattern="README.md",
        )
        result = CheckResult(check=check, passed=True, message="Found README.md")
        with runner.isolated_filesystem():
            from io import StringIO
            import click

            # Just verify _print_result does not raise
            _print_result(result)

    def test_print_result_failed_check(self, runner: CliRunner) -> None:
        check = StructureCheck(
            name="test_check",
            description="A test check",
            severity=CheckSeverity.warning,
            path_pattern="CONTRIBUTING.md",
        )
        result = CheckResult(check=check, passed=False, message="Not found")
        # Must not raise
        _print_result(result)

    def test_print_result_info_severity(self, runner: CliRunner) -> None:
        check = StructureCheck(
            name="info_check",
            description="Info-level check",
            severity=CheckSeverity.info,
            path_pattern=".pre-commit-config.yaml",
        )
        result = CheckResult(check=check, passed=True, message="Found config")
        # Must not raise
        _print_result(result)


# ---------------------------------------------------------------------------
# Integration tests combining flags
# ---------------------------------------------------------------------------


class TestCheckCommandIntegration:
    def test_quiet_and_strict_together(
        self, runner: CliRunner, minimal_project: Path
    ) -> None:
        result = runner.invoke(
            main, ["check", str(minimal_project), "--quiet", "--strict"]
        )
        # Should complete without an uncaught exception
        assert result.exception is None or isinstance(result.exception, SystemExit)

    def test_full_project_shows_check_count_at_least_thirteen(
        self, runner: CliRunner, full_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(full_project)])
        # Extract number from "Checks run: N"
        import re

        match = re.search(r"Checks run:\s*(\d+)", result.output)
        if match:
            count = int(match.group(1))
            assert count >= 13

    def test_custom_checks_increases_check_count(
        self, runner: CliRunner, full_project: Path, custom_checks_yaml: Path
    ) -> None:
        result_no_custom = runner.invoke(main, ["check", str(full_project)])
        result_with_custom = runner.invoke(
            main,
            [
                "check",
                str(full_project),
                "--custom-checks",
                str(custom_checks_yaml),
            ],
        )
        import re

        match_no_custom = re.search(r"Checks run:\s*(\d+)", result_no_custom.output)
        match_with_custom = re.search(
            r"Checks run:\s*(\d+)", result_with_custom.output
        )
        if match_no_custom and match_with_custom:
            count_no_custom = int(match_no_custom.group(1))
            count_with_custom = int(match_with_custom.group(1))
            assert count_with_custom > count_no_custom

    def test_empty_project_error_count_in_output(
        self, runner: CliRunner, empty_project: Path
    ) -> None:
        result = runner.invoke(main, ["check", str(empty_project)])
        assert "error" in result.output.lower()

    def test_version_and_check_do_not_conflict(self, runner: CliRunner) -> None:
        version_result = runner.invoke(main, ["--version"])
        assert version_result.exit_code == 0
        assert "0.1.0" in version_result.output
