# FileFlow CLI

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A cautious, cross-platform command-line file organizer for Windows, Linux, and macOS.**

Documentation: **English** | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md)

> **Status: Cycle 1 MVP in review.** File organization is implemented. Persistent operation manifests, undo, recursion, exclusions, and YAML configuration are **not** available yet. This project is not published on PyPI.

## Features available in Cycle 1

- Group files by extension, including recognized compound extensions such as `.tar.gz`.
- Group files into Documents, Images, Videos, Archives, Audio, or Other.
- Override category mappings using repeatable `--category Name=.ext,.ext` arguments.
- Optionally add modification-date folders (`YYYY/MM`, **UTC**).
- Choose independent source and destination directories.
- Preview every proposed move with `--dry-run`; preview creates **no** directories.
- Resolve existing-name conflicts with numbered suffixes such as `report (1).pdf`.
- Refuse to replace any existing target, including a target created after planning.
- Skip directories, hidden dotfiles, and symbolic-link entries.

## Requirements and installation

Python **3.14 or newer**. The current MVP requires only Typer and Rich at runtime. Clone the repository and install it locally:

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
# Activate the environment using your shell's standard activation command.
python -m pip install -e .
fileflow --help
fileflow organize --help
~~~

**Note:** Until the first PR is merged, use the `feat/cycle-1-safe-file-organizer` branch to evaluate the MVP.

## Commands

Preview moving files from an inbox into a separate directory:

~~~bash
fileflow organize ./inbox --destination ./organized --dry-run
~~~

Execute grouping by extension:

~~~bash
fileflow organize ./inbox -d ./organized
~~~

Group by built-in categories and add custom extensions:

~~~bash
fileflow organize ./inbox -d ./organized --mode category --category "Research=.pdf,.ipynb"
~~~

Group by extension, then UTC modification year and month:

~~~bash
fileflow organize ./inbox -d ./organized --by-date
~~~

Equivalent invocation without a console-script PATH entry:

~~~bash
python -m fileflow organize ./inbox -d ./organized --dry-run
~~~

Each run displays a Rich table and a summary. Exit codes: `0` = successful execution or preview, `1` = one or more move failures, `2` = invalid plan or paths. The CLI only scans the **immediate children** of the source directory during Cycle 1.

## Safety model

Planning is separate from execution. FileFlow rejects identical or nested source/destination directories, validates paths and basic access, and refuses symlinks in input paths. During execution, each destination is created with exclusive file creation, so pre-existing data is not overwritten. Source metadata is checked before and after copying. The source is removed **only after** a successful copy and metadata check. A failed operation normally cleans up its new destination file, preserving the original; errors are reported individually.

Before using the tool on important files, make a backup and inspect a dry run. Permission checks are best-effort and runtime failures remain possible.

## YAML configuration and undo

**Planned for Cycle 2, not implemented in this version.** A future `--config` flag will load YAML mappings and exclusions, and `undo` will consume a persistent operation manifest. Neither command is currently advertised as working. Do not expect this MVP to recover already executed moves automatically.

## Architecture

~~~text
src/fileflow/
  cli.py       Typer commands and Rich rendering
  models.py    Immutable plans, operations, results
  rules.py     Categories, extensions, input rules
  planner.py   Validation, collision resolution, dry-run planning
  executor.py  Exclusive copies, checks, and guarded source removal
  __main__.py  python -m entry point
tests/         Isolated pytest tests using tmp_path
.github/workflows/ci.yml  Cross-platform quality, tests, packaging
~~~

## Tests and quality

All file-changing tests use pytest's `tmp_path`; they never touch personal directories. Install test dependencies:

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
~~~

CI is configured for pull requests targeting `main` and pushes to `main`, using GitHub-hosted Ubuntu, Windows, and macOS runners with Python 3.14. The badge reflects the actual GitHub Actions state; it is not a claimed test result.

## Known limitations and roadmap

- The MVP is **not recursive**. Exclusion patterns, YAML, persistent logs, and undo are planned.
- Hidden files and links are skipped without an override.
- Date grouping uses UTC, not the machine's local timezone.
- Existing destination directories may be created before a later file fails; empty directories are not rolled back.
- Copy-and-unlink is not an atomic transaction. Abrupt termination may leave a partial destination file; it does not promise crash-safe rollback.
- Concurrent hostile filesystem modifications and sophisticated directory-swap attacks are outside the current threat model.
- Files can change during processing; FileFlow detects common changes through inode, size, and modification-time metadata, but cannot guarantee an adversarially immutable snapshot.

## License

MIT. See [LICENSE](LICENSE).
