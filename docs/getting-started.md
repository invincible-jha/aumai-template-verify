# Getting Started with aumai-template-verify

This guide walks you from installation to running your first structural verification and setting up
automated checks in CI.

---

## Prerequisites

- Python 3.11 or later
- `pip` (or `uv`, `poetry`, `pdm`)
- A Python project directory you want to verify

Check your Python version:

```bash
python --version
# Python 3.11.x or higher
```

---

## Installation

### From PyPI (recommended)

```bash
pip install aumai-template-verify
```

Verify:

```bash
aumai-template-verify --version
```

### From source

```bash
git clone https://github.com/aumai/aumai-template-verify.git
cd aumai-template-verify
pip install -e .
```

### Development mode (with test/lint dependencies)

```bash
git clone https://github.com/aumai/aumai-template-verify.git
cd aumai-template-verify
pip install -e ".[dev]"
make test
make lint
```

---

## Your First Verification

This tutorial verifies a real project directory step by step.

### Step 1 — Choose a project to check

Pick any Python project on your machine. If you do not have one, create a minimal structure:

```bash
mkdir my-agent
cd my-agent
mkdir src tests .github
mkdir .github/workflows
touch README.md LICENSE pyproject.toml AGENTS.md CONTRIBUTING.md SECURITY.md
touch .github/workflows/ci.yml
```

### Step 2 — Run the check

```bash
aumai-template-verify check ./my-agent
```

If you created the minimal structure above, you will see output like:

```
Project: /home/user/my-agent
Checks run: 13  |  Score: 76.9%

  PASS  [error]    readme_exists — Found: README.md
  PASS  [error]    agents_md_exists — Found: AGENTS.md
  PASS  [error]    license_exists — Found: LICENSE
  PASS  [error]    pyproject_exists — Found: pyproject.toml
  PASS  [error]    src_directory_exists — Found: src
  PASS  [warning]  contributing_exists — Found: CONTRIBUTING.md
  PASS  [warning]  security_exists — Found: SECURITY.md
  PASS  [warning]  tests_directory_exists — Found: tests
  PASS  [warning]  github_workflows_exists — Found: .github/workflows
  FAIL  [warning]  pyproject_has_mypy_strict — Pattern 'strict\s*=\s*true' not found in pyproject.toml
  FAIL  [info]     py_typed_marker_exists — No files matching 'src/**/py.typed' found.
  FAIL  [info]     pyproject_has_ruff — Pattern '\[tool\.ruff\]' not found in pyproject.toml
  FAIL  [info]     pre_commit_config_exists — Not found: .pre-commit-config.yaml

PASSED (1 warning(s))
```

The project passes because all `error`-severity checks passed. The warnings and info checks
indicate areas to improve.

### Step 3 — Understand the output

Each line shows:
- `PASS` or `FAIL` (coloured green / red)
- `[severity]` — error, warning, or info (coloured red, yellow, blue)
- Check name
- A message explaining what was found or not found

The summary line shows the total score and the overall verdict.

### Step 4 — Fix a failing check

Add mypy strict mode to `pyproject.toml`:

```toml
[tool.mypy]
strict = true
```

Re-run the check:

```bash
aumai-template-verify check ./my-agent
```

The `pyproject_has_mypy_strict` warning should now show `PASS`.

### Step 5 — Use strict mode for CI

To ensure warnings also block your CI pipeline:

```bash
aumai-template-verify check . --strict
```

This exits with code 1 if any `warning`-severity check fails, not just `error`-severity ones.

---

## Common Patterns

### Pattern 1 — CI gate in GitHub Actions

Add to `.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  verify-structure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install aumai-template-verify
      - run: aumai-template-verify check . --strict

  tests:
    runs-on: ubuntu-latest
    needs: verify-structure
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest
```

The `verify-structure` job runs first and blocks `tests` from running if the project structure is
non-compliant.

---

### Pattern 2 — Custom checks for your team's standards

Create `team-checks.yaml`:

```yaml
checks:
  - name: changelog_exists
    description: "CHANGELOG.md is required for release notes."
    severity: warning
    path_pattern: "CHANGELOG.md"

  - name: docs_dir_exists
    description: "A docs/ directory must be present."
    severity: info
    path_pattern: "docs"

  - name: apache_license
    description: "LICENSE must declare Apache 2.0."
    severity: error
    path_pattern: "LICENSE"
    content_pattern: "Apache License.*Version 2\\.0"
```

Run with your custom checks appended to the built-in set:

```bash
aumai-template-verify check . --custom-checks team-checks.yaml
```

---

### Pattern 3 — Programmatic use in a Python script

Useful for reporting across multiple repositories:

```python
#!/usr/bin/env python3
"""Check all repos in a workspace directory and print a summary table."""

from pathlib import Path
from aumai_template_verify import TemplateVerifier

workspace = Path("./workspace")
verifier = TemplateVerifier()

print(f"{'Repo':<30} {'Score':>6}  {'Status'}")
print("-" * 50)

for repo_dir in sorted(workspace.iterdir()):
    if not repo_dir.is_dir():
        continue
    report = verifier.verify(str(repo_dir))
    status = "PASS" if report.passed else "FAIL"
    print(f"{repo_dir.name:<30} {report.score:>5.1f}%  {status}")
```

---

### Pattern 4 — Programmatic use in pytest

Validate that your own project always meets the standard as part of the test suite:

```python
# tests/test_project_structure.py
from pathlib import Path
from aumai_template_verify import TemplateVerifier


def test_project_structure_passes_all_error_checks() -> None:
    """The project must always satisfy all error-severity structural checks."""
    project_root = Path(__file__).parent.parent
    report = TemplateVerifier().verify(str(project_root))

    failed_errors = [
        r for r in report.failed_results
        if r.check.severity.value == "error"
    ]
    assert failed_errors == [], (
        f"Structural compliance errors: "
        + ", ".join(r.check.name for r in failed_errors)
    )
```

---

### Pattern 5 — Quiet output for CI logs

When running across many repos, `--quiet` shows only the problems:

```bash
for dir in ./workspace/*/; do
  echo "Checking $dir..."
  aumai-template-verify check "$dir" --quiet --strict || true
done
```

---

## Troubleshooting FAQ

### `aumai-template-verify: command not found`

The package is not installed, or it is installed into a virtual environment that is not activated.

```bash
# Check if it is installed
pip show aumai-template-verify

# Activate your venv
source .venv/bin/activate

# Or install globally
pip install aumai-template-verify
```

---

### `Verification error: [Errno 2] No such file or directory`

The `PROJECT_PATH` argument does not exist.

```bash
# Always check the path first
ls ./my-project

# Use an absolute path if relative paths cause confusion
aumai-template-verify check /absolute/path/to/project
```

---

### `Failed to load custom checks: Custom check config must be a YAML mapping with a 'checks' key.`

Your custom checks YAML file must have a top-level `checks` key:

```yaml
# Wrong:
- name: my_check
  description: "..."
  path_pattern: "some/file"

# Correct:
checks:
  - name: my_check
    description: "..."
    path_pattern: "some/file"
```

---

### A custom check fails with `At least one of path_pattern or content_pattern must be provided`

Every `StructureCheck` requires at least one of `path_pattern` or `content_pattern`. A check with
neither cannot be evaluated.

```yaml
# Wrong — no criterion:
checks:
  - name: bad_check
    description: "This check has no criterion."
    severity: warning

# Correct:
checks:
  - name: good_check
    description: "Checks for a docs directory."
    severity: info
    path_pattern: "docs"
```

---

### The `pyproject_has_mypy_strict` check fails even though mypy strict is configured

The check looks for the regex `strict\s*=\s*true` (case-insensitive) anywhere in `pyproject.toml`.
Common reasons it can fail:

- The setting is under a profile name rather than `[tool.mypy]` directly
- `strict = true` is commented out
- You are using `--strict` on the command line rather than in config

Ensure your `pyproject.toml` has:

```toml
[tool.mypy]
strict = true
```

---

### `--strict` causes the CI to fail but `--strict` was not intended

The `--strict` flag makes warnings count as failures. Remove it from your CI command if you only
want `error`-severity checks to block CI:

```bash
# Only errors block CI:
aumai-template-verify check .

# Errors AND warnings block CI:
aumai-template-verify check . --strict
```

---

### Score is lower than expected

The score is `passed_count / total_check_count * 100`. If you are loading custom checks, they are
included in the denominator. A check that raises an exception internally is counted as failed.

To see exactly which checks are failing, run without `--quiet`:

```bash
aumai-template-verify check .
```

Every check — passing and failing — will be listed.
