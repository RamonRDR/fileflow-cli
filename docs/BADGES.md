# README badge inventory and verification

The canonical README is `README.md` (English), with equivalent Portuguese and Spanish versions. All three headers display the same **14** badge URLs.

| Badge | Evidence | Indicator |
| --- | --- | --- |
| CI | `.github/workflows/ci.yml` | Dynamic |
| Python 3.14 | CI `setup-python`, `pyproject.toml` | Static version |
| Version 0.1.0 | `pyproject.toml` `[project].version` | Source version; **not** a PyPI release |
| MIT | `LICENSE`, `pyproject.toml` | Static |
| Typer | `pyproject.toml`, `src/fileflow/cli.py` | Runtime library |
| Rich | `pyproject.toml`, `src/fileflow/cli.py` | Runtime library |
| PyYAML | `pyproject.toml`, `src/fileflow/config.py` | Runtime library |
| Hatchling | `pyproject.toml` `[build-system]` | Packaging backend |
| pytest 92 passing | [GitHub Actions run #42732136463](https://github.com/RamonRDR/fileflow-cli/actions/runs/42732136463) on Ubuntu, Windows and macOS | Static number, checked against CI |
| Ruff lint + format | CI `ruff check .` and `ruff format --check .` | CI-gated |
| Build / verified wheel | CI `python -m build` and `examples/wheel_smoke.py` | CI-gated |
| CLI smoke | CI command-line `--help` checks | CI-gated |
| E2E demo | CI `python examples/demo.py` | CI-gated |
| Windows / Linux / macOS | CI OS matrix | CI-gated |

## Maintaining the pytest count

CI executes `python -m pytest -q --junitxml=pytest-results.xml`, followed by `python examples/verify_readme_badges.py pytest-results.xml`.

The verifier calculates **passing = total − failures − errors − skipped** from the JUnit XML produced by pytest, verifies all three README badges, **the published counts in the three README descriptions and this inventory**, checks that the **14 badge URLs** are identical, confirms the language navigation links and the declared project version in `pyproject.toml`, and validates local Markdown link targets. Parameterized cases are counted by pytest, not as distinct function definitions.

When tests are added, removed or skipped, update the `pytest-N%20passing` badges, **test-count descriptions** in all three READMEs and this inventory **in the same PR**. CI fails until every displayed count matches the actual result. The script only reads files: it never commits to `main`, requires no extra secrets and publishes nothing.

CI is the only live badge. All other badges are descriptive, not independent status APIs. The declared dependency ranges do not justify advertising exact Typer/Rich/PyYAML/Hatchling versions. Docker, Pydantic, databases, mypy, API docs, and measured test coverage do **not** exist in this project and are intentionally omitted. The historical one-time branch-cleanup workflow was removed after successful use; it was never a regular quality gate.
