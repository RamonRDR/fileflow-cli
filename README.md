# FileFlow CLI

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A cautious, cross-platform file organizer with YAML rules, preview mode, persistent operation logs and conflict-safe undo.**

🇬🇧 English · [🇧🇷 Português](README.pt-BR.md) · [🇪🇸 Español](README.es.md)

> **Release status:** feature-complete candidate, pending final review and owner-approved merges. Not published on PyPI. While the pull-request stack is open, install the latest feature branch rather than `main`.

FileFlow is designed for real local-file automation and as a portfolio demonstration of modular Python engineering, explicit safety decisions and multi-platform testing.

## Features

- Group files by **extension** (`pdf`, `jpg`, `tar.gz` or `no-extension`) or by **category** (Documents, Images, Videos, Archives, Audio and Other).
- Configure new categories with repeatable CLI flags or versioned **YAML** rules.
- Optionally add **UTC modification-date** subfolders (`YYYY/MM`).
- Select independent source and destination directories.
- Opt into recursive scanning. File and directory symlinks are never followed.
- Exclude files or whole directories using case-insensitive glob patterns.
- Use `--dry-run` to preview all intended moves without creating directories or manifests.
- Avoid overwriting pre-existing files, including destinations created after planning. Resolve planned duplicates using numbered filenames.
- Persist a JSON manifest with each run's successes, failures and SHA-256 checksums.
- Run `undo` with integrity checks and a separate dry-run, refusing conflicting original paths and modified destinations.
- Review a Rich terminal table, summary counts, and clear exit codes.

## Technology stack

Python **3.14+**, Typer, Rich, PyYAML, pathlib and the Python standard library. Hatchling builds the package; pytest and Ruff provide the quality gates. GitHub Actions validates Linux, Windows and macOS. No cloud service, database, daemon or credentials are required.

## Installation

Clone a revision containing the feature-complete PR stack:

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
~~~

Activate your environment: Windows PowerShell `.venv\Scripts\Activate.ps1`, Linux/macOS `source .venv/bin/activate`. Then:

~~~bash
python -m pip install -e .
fileflow --help
fileflow organize --help
fileflow undo --help
~~~

The package is **not** published to PyPI. Before the stacked PRs are merged, check out the latest development branch; the default branch does not yet include this implementation. You may also invoke the CLI with `python -m fileflow`.

## Quick start

Preview without changing a single file:

~~~bash
fileflow organize ./inbox --destination ./organized --dry-run
~~~

Move by extension, category or UTC modification date:

~~~bash
fileflow organize ./inbox -d ./organized
fileflow organize ./inbox -d ./organized --mode category
fileflow organize ./inbox -d ./organized --by-date
~~~

Use a custom category or scan recursively with exclusions:

~~~bash
fileflow organize ./inbox -d ./organized --mode category --category "Research=.pdf,.ipynb"
fileflow organize ./inbox -d ./organized --recursive --exclude "*.tmp" --exclude "cache/**"
~~~

Organize with YAML rules:

~~~bash
fileflow organize ./inbox -d ./organized --config examples/config.yaml --dry-run
fileflow organize ./inbox -d ./organized --config examples/config.yaml
~~~

Every real run that has candidate files prints a **manifest path**, such as `<destination>/.fileflow/manifests/<run-id>.json`. Use the actual printed path to verify and then reverse moves:

~~~bash
fileflow undo "/path/to/organized/.fileflow/manifests/<run-id>.json" --dry-run
fileflow undo "/path/to/organized/.fileflow/manifests/<run-id>.json"
~~~

These are command examples, not fabricated output from an execution.

## YAML configuration

~~~yaml
version: 1
mode: category
recursive: true
by_date: false
categories:
  Research:
    - .pdf
    - .ipynb
exclude:
  - "*.tmp"
  - "cache/**"
~~~

The schema is strict: unknown keys, invalid extension strings, malformed patterns and unexpected value types are rejected. YAML uses `safe_load`. Built-in categories remain available, but explicit overrides reassign their extensions. Assigning an extension twice is rejected.

`--mode` overrides YAML mode. `--recursive`, `--by-date`, `--category` and `--exclude` add to or enable YAML settings; they do not disable a YAML `true` flag. Exclusions are matched against names or source-relative paths, using forward slashes and case-insensitive comparison. `cache/**` skips the cache folder itself.

## Safety and undo

1. **Read-only plan:** Dry-run only inspects paths and displays the plan; it never writes files or manifests.
2. **Non-overlapping roots:** The source and destination must be different, non-nested directories. Directly selected symlink roots are rejected; ancestor aliases (such as macOS /var) resolve to canonical physical paths. Scanned links and hidden entries are ignored.
3. **Exclusive destinations:** Plans choose numbered suffixes for existing names, and the copy uses `xb` so a late destination cannot be silently overwritten.
4. **Copy first:** The executor copies data, flushes/synchronizes it, reads back a SHA-256 digest, rechecks source metadata and only then removes the source pathname.
5. **Persistent journal:** A unique run manifest is written before the first copy and updated after each success or failure.
6. **Guarded undo:** Restores only recorded successful moves, checks the destination's size and SHA-256, refuses existing original paths, and records successful reversals.

There is **no permanent-delete command**. Successful moves remove the original pathname only after copying, and successful undo removes the moved pathname only after restoration. Back up irreplaceable data and run a dry-run before touching important files.

**Limitations matter:** Copy-and-remove is not an atomic filesystem transaction. A crash can leave a partial new file or a `planned` manifest entry even after a copy has completed. Such entries require **manual reconciliation**; they are never automatically undone. The tool does not fully defend against malicious concurrent directory swaps. Read [Security model and limitations](docs/SECURITY.md).

Exit codes: `0` successful preview/execution, `1` operational failures or undo conflicts, `2` invalid configuration, paths or manifest.

## Project architecture

~~~text
src/fileflow/
  cli.py       Typer commands and Rich output
  config.py    Strict YAML parsing and validation
  rules.py     Category and exclusion rules
  planner.py   Root safety, enumeration, collision-free plan
  models.py    Immutable operation models
  executor.py  Exclusive, verified copy-before-unlink
  journal.py   Persistent manifests and conflict-safe undo
  __main__.py  python -m fileflow entry point
tests/         Disposable pytest fixtures
examples/      YAML configuration and reproducible demo
docs/          Security model and engineering decisions
.github/workflows/ci.yml  Multi-platform CI
~~~

The architecture separates CLI, rule validation, planning, execution and reversibility. See [Engineering decisions](docs/DECISIONS.md).

## Tests, builds and real terminal demonstration

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
python examples/demo.py
~~~

All tests that modify files use isolated pytest `tmp_path` directories. The demonstration creates temporary input/output folders, runs the **real CLI** in subprocesses, previews an operation, demonstrates a destination collision, executes the move and reverses it. It doesn't touch personal files. Its real output is included in the **Demo CLI end-to-end** step of [GitHub Actions](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml) on Ubuntu, Windows and macOS. There are no fabricated screenshots or claimed benchmarks.

The workflow runs on pull requests and pushes to `main`. The badge reflects GitHub's actual state, not a guarantee that unmerged features are already on the default branch.

## Known limitations

- Not a crash-proof transaction; partial files or outdated journal records can remain after sudden termination.
- No defense against adversarial filesystem races, concurrent organizing processes or all network filesystem behaviors.
- Trust only your own local manifests; they contain absolute paths and should not be edited or shared.
- Recursive mode collects files into category/extension folders, **flattening** their original hierarchy. Empty source directories are left in place.
- Hidden items, symlinks and special files are ignored. Time grouping is UTC.
- Cross-platform filename handling and permission checks depend on the underlying filesystem.
- This package is a local automation tool, not an enterprise backup system.

## License

[MIT License](LICENSE). Copyright © 2026 Ramon Rodriguez.
