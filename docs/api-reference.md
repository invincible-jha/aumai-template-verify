# API Reference — aumai-template-verify

Complete reference for all public classes, functions, and models exposed by `aumai-template-verify`.

---

## Module `aumai_template_verify`

The package re-exports all public symbols from `core` and `models` at the top level.

```python
from aumai_template_verify import (
    # Core
    TemplateVerifier,
    CustomCheckLoader,
    # Models
    CheckResult,
    CheckSeverity,
    StructureCheck,
    VerificationReport,
)
```

**Package version:** `aumai_template_verify.__version__` (`str`)

---

## Module `aumai_template_verify.core`

Contains the verification engine and the custom check loader.

---

### `TemplateVerifier`

```python
class TemplateVerifier:
    def __init__(
        self,
        extra_checks: list[StructureCheck] | None = None,
    ) -> None: ...
```

Verifies a project directory against the AumAI best-practice checklist.

On construction, the 13 built-in checks are loaded. Any `extra_checks` are appended after the
built-in set, so they run alongside (not instead of) the standard checks.

**Constructor parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `extra_checks` | `list[StructureCheck] \| None` | `None` | Additional checks to run alongside the built-in set. Pass `None` or omit to use only built-in checks. |

**Example:**

```python
from aumai_template_verify import TemplateVerifier

# Built-in checks only
verifier = TemplateVerifier()

# Built-in checks plus custom additions
verifier = TemplateVerifier(extra_checks=[
    StructureCheck(
        name="changelog_exists",
        description="CHANGELOG.md is required.",
        severity=CheckSeverity.warning,
        path_pattern="CHANGELOG.md",
    )
])
```

---

#### `TemplateVerifier.verify`

```python
def verify(self, project_path: str) -> VerificationReport:
```

Run all configured checks against the specified project directory and return a report.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `project_path` | `str` | Absolute or relative path to the project root. Resolved to an absolute path internally via `Path.resolve()`. |

**Returns:** `VerificationReport` — contains per-check results, an aggregate score, and an overall pass/fail verdict.

**Behavior:**
- The path is always resolved to an absolute path before checks run.
- Each check is applied independently; a failure in one does not stop others.
- Exceptions raised during individual check evaluation are caught and recorded as failed results with the exception message.
- `report.passed` is `True` only when all `error`-severity checks pass.

**Example:**

```python
report = verifier.verify("./my-project")

print(f"Score: {report.score:.1f}%")
print(f"Overall: {'PASSED' if report.passed else 'FAILED'}")
print(f"Errors: {report.error_count}, Warnings: {report.warning_count}")

for result in report.failed_results:
    print(f"  [{result.check.severity.value}] {result.check.name}: {result.message}")
```

---

### `CustomCheckLoader`

```python
class CustomCheckLoader:
    def load(self, config_path: str) -> list[StructureCheck]: ...
```

Parses a YAML file and returns a list of `StructureCheck` instances suitable for passing to
`TemplateVerifier(extra_checks=...)`.

---

#### `CustomCheckLoader.load`

```python
def load(self, config_path: str) -> list[StructureCheck]:
```

Read and validate a YAML custom check configuration file.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `config_path` | `str` | Path to the YAML file. Must be readable and contain valid YAML. |

**Returns:** `list[StructureCheck]` — validated check objects ready for use.

**Raises:**
- `ValueError` — if the YAML file does not contain a top-level `checks` key, or if any check entry fails Pydantic validation.
- `OSError` — if the file cannot be read.
- `yaml.YAMLError` — if the file content is not valid YAML.

**Expected YAML format:**

```yaml
checks:
  - name: my_check
    description: "Human-readable description."
    severity: warning           # optional, defaults to error
    path_pattern: "some/path"   # at least one of path_pattern or content_pattern required
    content_pattern: "regex"    # optional — requires path_pattern to also be set
```

**Example:**

```python
from aumai_template_verify import CustomCheckLoader, TemplateVerifier

loader = CustomCheckLoader()
extra = loader.load("team-checks.yaml")

verifier = TemplateVerifier(extra_checks=extra)
report = verifier.verify(".")
```

---

## Module `aumai_template_verify.models`

All Pydantic models used by the verification engine. Fields are validated at construction time.

---

### `CheckSeverity`

```python
class CheckSeverity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"
```

Severity level for a structure check, in decreasing order of importance.

| Value | CLI color | Affects `report.passed` | Affects `--strict` exit code |
|---|---|---|---|
| `error` | red | Yes — `False` if any error fails | Yes |
| `warning` | yellow | No | Yes (only with `--strict`) |
| `info` | blue | No | No |

---

### `StructureCheck`

```python
class StructureCheck(BaseModel):
    name: str
    description: str
    severity: CheckSeverity = CheckSeverity.error
    path_pattern: str | None = None
    content_pattern: str | None = None
```

A single check definition that can be applied to a project directory.

**Fields:**

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `name` | `str` | required | Non-empty after stripping | Short identifier for the check. Used in CLI output and error messages. |
| `description` | `str` | required | — | Human-readable explanation of what is being checked and why. |
| `severity` | `CheckSeverity` | `error` | Enum value | Severity level when this check fails. |
| `path_pattern` | `str \| None` | `None` | — | Glob or exact path relative to the project root. The file/directory must exist to pass. Supports `*` and `**` wildcards. |
| `content_pattern` | `str \| None` | `None` | Valid Python regex | Regex pattern that must appear in the matched file. Searched with `IGNORECASE | MULTILINE`. |

**Validation:**
- `name` must be non-empty after stripping whitespace.
- At least one of `path_pattern` or `content_pattern` must be non-`None` (enforced by a Pydantic model validator).

**Examples:**

```python
from aumai_template_verify import StructureCheck, CheckSeverity

# Path existence check
check = StructureCheck(
    name="license_exists",
    description="A LICENSE file must be present.",
    severity=CheckSeverity.error,
    path_pattern="LICENSE",
)

# Content check (path + regex)
check = StructureCheck(
    name="has_apache_header",
    description="LICENSE must declare Apache 2.0.",
    severity=CheckSeverity.error,
    path_pattern="LICENSE",
    content_pattern=r"Apache License.*Version 2\.0",
)

# Glob path check
check = StructureCheck(
    name="py_typed_exists",
    description="A py.typed marker must exist inside src/.",
    severity=CheckSeverity.info,
    path_pattern="src/**/py.typed",
)
```

---

### `CheckResult`

```python
class CheckResult(BaseModel):
    check: StructureCheck
    passed: bool
    message: str
```

The outcome of applying a single `StructureCheck` to a project directory.

**Fields:**

| Field | Type | Description |
|---|---|---|
| `check` | `StructureCheck` | The check definition that was applied. |
| `passed` | `bool` | `True` if the check criterion was satisfied. |
| `message` | `str` | A human-readable explanation: which file was found, which pattern matched or did not match. |

**Example:**

```python
result = report.results[0]
print(result.check.name)   # "readme_exists"
print(result.passed)       # True
print(result.message)      # "Found: README.md"
```

---

### `VerificationReport`

```python
class VerificationReport(BaseModel):
    project_path: str
    results: list[CheckResult] = []
    score: float  # 0.0 – 100.0
    passed: bool
```

Summary of all check results for a project directory. Returned by `TemplateVerifier.verify()`.

**Fields:**

| Field | Type | Description |
|---|---|---|
| `project_path` | `str` | Absolute path of the project that was verified. |
| `results` | `list[CheckResult]` | Individual check outcomes, in the order checks were run. |
| `score` | `float` | Percentage of checks that passed (0.0–100.0, rounded to one decimal place). |
| `passed` | `bool` | `True` when all `error`-severity checks passed. Warnings and info failures do not affect this field. |

**Properties:**

#### `VerificationReport.failed_results`

```python
@property
def failed_results(self) -> list[CheckResult]:
```

Returns only the `CheckResult` entries where `passed` is `False`.

Useful for iterating over just the failures without filtering manually.

```python
for result in report.failed_results:
    print(f"{result.check.name}: {result.message}")
```

---

#### `VerificationReport.error_count`

```python
@property
def error_count(self) -> int:
```

Count of failed checks with `severity == CheckSeverity.error`.

Used by the CLI to determine whether to exit with code 1.

```python
if report.error_count > 0:
    print(f"{report.error_count} blocking error(s) found")
```

---

#### `VerificationReport.warning_count`

```python
@property
def warning_count(self) -> int:
```

Count of failed checks with `severity == CheckSeverity.warning`.

Used by the CLI in `--strict` mode to determine whether to exit with code 1.

```python
if report.warning_count > 0:
    print(f"{report.warning_count} warning(s) found")
```

---

## Built-in Check Definitions

The following checks are always applied by `TemplateVerifier` regardless of `extra_checks`.
They are defined as a module-level constant `_BUILTIN_CHECKS` in `core.py`.

| name | severity | path_pattern | content_pattern |
|---|---|---|---|
| `readme_exists` | error | `README.md` | — |
| `contributing_exists` | warning | `CONTRIBUTING.md` | — |
| `security_exists` | warning | `SECURITY.md` | — |
| `agents_md_exists` | error | `AGENTS.md` | — |
| `license_exists` | error | `LICENSE` | — |
| `pyproject_exists` | error | `pyproject.toml` | — |
| `src_directory_exists` | error | `src` | — |
| `tests_directory_exists` | warning | `tests` | — |
| `github_workflows_exists` | warning | `.github/workflows` | — |
| `py_typed_marker_exists` | info | `src/**/py.typed` | — |
| `pyproject_has_mypy_strict` | warning | `pyproject.toml` | `strict\s*=\s*true` |
| `pyproject_has_ruff` | info | `pyproject.toml` | `\[tool\.ruff\]` |
| `pre_commit_config_exists` | info | `.pre-commit-config.yaml` | — |

---

## CLI Reference

### `aumai-template-verify check`

```
aumai-template-verify check PROJECT_PATH [--strict] [--custom-checks FILE] [--quiet]
```

**Arguments and options:**

| Name | Type | Description |
|---|---|---|
| `PROJECT_PATH` | positional argument | Path to the project root directory |
| `--strict` | flag | Exit 1 when any `warning`-severity check fails (in addition to errors) |
| `--custom-checks FILE` | path | YAML file with additional checks to run |
| `--quiet`, `-q` | flag | Only print failing checks |

**Exit codes:**

| Code | Condition |
|---|---|
| `0` | All `error`-severity checks passed (and no `--strict` warnings failed) |
| `1` | One or more `error`-severity checks failed |
| `1` | `--strict` and one or more `warning`-severity checks failed |
| `1` | Custom checks file could not be loaded |
| `1` | An unexpected exception occurred during verification |
