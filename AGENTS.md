# Repository guidance

FileFlow is a cross-platform Python CLI that moves user files. **Preventing data loss is more important than completing a move.**

## Code Review Rules

### Never overwrite user files
- Flag any path that can replace or truncate an existing destination, including conflicts that arise after planning. Safe behavior: reject the operation and preserve both files, or select an unused destination name **before** execution with exclusive creation.
- Flag cleanup code that might delete a pre-existing destination after an unsuccessful move. Cleanup must only affect files created by the current operation.

### Keep previews and failures non-destructive
- A dry run must not create directories, write files, change permissions, or delete source files.
- Reject changes that remove the source before successfully completing and checking the destination copy. Report partial failures clearly. Ordinary errors should preserve the original file whenever possible.

### Respect filesystem boundaries
- Source and destination must not be identical or nested, including through symbolic links.
- Do not follow symbolic links found while scanning. Treat potentially unsafe path changes or broken links conservatively.
- All file-mutating tests must use disposable pytest fixtures (such as `tmp_path`), never paths belonging to a developer or CI runner.

## Project boundaries

- Cycle 1 has extension/category/date grouping and a dry run.
- YAML, recursion, exclusions, persistent logs, and conflict-safe undo belong to Cycle 2; never claim those features exist before implementation and passing tests.
- Python 3.14, Ruff, pytest, and GitHub Actions are quality gates. Do not spend review findings on formatting already enforced by CI.
- Do not merge into `main` or publish packages without owner approval.
