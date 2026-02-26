"""Pydantic models for aumai-template-verify."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class CheckSeverity(str, Enum):
    """Severity level for a structure check."""

    error = "error"
    warning = "warning"
    info = "info"


class StructureCheck(BaseModel):
    """A single check definition that can be applied to a project directory."""

    name: str = Field(description="Short identifier for this check")
    description: str = Field(description="Human-readable explanation of what is being checked")
    severity: CheckSeverity = Field(
        default=CheckSeverity.error, description="Severity when this check fails"
    )
    path_pattern: str | None = Field(
        default=None,
        description="Glob pattern relative to the project root; file must exist to pass",
    )
    content_pattern: str | None = Field(
        default=None,
        description="Regex pattern that must appear somewhere in the matched file",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        """Ensure check name is non-empty."""
        if not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> "StructureCheck":
        """At least path_pattern or content_pattern must be set."""
        if self.path_pattern is None and self.content_pattern is None:
            raise ValueError(
                "At least one of path_pattern or content_pattern must be provided"
            )
        return self


class CheckResult(BaseModel):
    """The outcome of applying a single StructureCheck."""

    check: StructureCheck = Field(description="The check that was applied")
    passed: bool = Field(description="True when the check was satisfied")
    message: str = Field(description="Details about why the check passed or failed")


class VerificationReport(BaseModel):
    """Summary of all check results for a project directory."""

    project_path: str = Field(description="Absolute path of the project that was verified")
    results: list[CheckResult] = Field(
        default_factory=list, description="Individual check outcomes"
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of checks that passed (0-100)",
    )
    passed: bool = Field(
        default=False,
        description="True when all error-severity checks passed",
    )

    @property
    def failed_results(self) -> list[CheckResult]:
        """Return only the failed check results."""
        return [r for r in self.results if not r.passed]

    @property
    def error_count(self) -> int:
        """Count of failed error-severity checks."""
        return sum(
            1 for r in self.results
            if not r.passed and r.check.severity == CheckSeverity.error
        )

    @property
    def warning_count(self) -> int:
        """Count of failed warning-severity checks."""
        return sum(
            1 for r in self.results
            if not r.passed and r.check.severity == CheckSeverity.warning
        )


__all__ = [
    "CheckSeverity",
    "StructureCheck",
    "CheckResult",
    "VerificationReport",
]
