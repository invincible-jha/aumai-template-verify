"""AumAI TemplateVerify — validate agent project structures against best practices."""

from aumai_template_verify.core import CustomCheckLoader, TemplateVerifier
from aumai_template_verify.models import (
    CheckResult,
    CheckSeverity,
    StructureCheck,
    VerificationReport,
)

__version__ = "0.1.0"

__all__ = [
    "TemplateVerifier",
    "CustomCheckLoader",
    "CheckResult",
    "CheckSeverity",
    "StructureCheck",
    "VerificationReport",
]
