# Engineering decisions

## ADR 0001: Plan before execution

`planner.py` computes immutable Move objects; `executor.py` performs exclusive copies only after validation. Dry-run never invokes filesystem mutations. There is no database or task queue.

## ADR 0002: Verify before unlinking

A plain rename could replace an existing file or fail across volumes. The executor uses exclusive target creation (`xb`), reads back and compares SHA-256 digests for the source and copied destination, and checks source identity before unlinking. This favors safety over raw speed; it is not an atomic transaction.

## ADR 0003: Versioned YAML without Pydantic

PyYAML `safe_load` plus small explicit validators is sufficient for this compact schema. Unknown keys and wrong types are rejected. A model framework would add a runtime dependency without much value at present.

## ADR 0004: JSON manifests for undo

A hidden destination-side manifest stores paths, status, and SHA-256 of successful moves. Undo validates roots, destinations, hashes and original path availability, while allowing a missing source root to be recreated. A conservative 10 MB preflight bound prevents writing a manifest that undo would subsequently refuse to read. Incomplete `planned` entries are not automatically reversed.

## ADR 0005: Stacked PRs and CI

PR #1 (MVP), #2 (YAML/recursion/exclusions), #3 (manifests/undo) and #4 (documentation, demo and release readiness) were squash-merged sequentially into `main` following owner approval. The consolidated Codex review PR #5 was closed without merging. Codex's final review on the release candidate found no unresolved issues. GitHub Actions passed 92 tests per platform on Windows, Ubuntu and macOS, plus Ruff, package build and a real CLI demonstration.
