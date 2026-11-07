# Engineering decisions (development candidate)

## ADR 0001: Plan before execution

`planner.py` computes immutable Move objects; `executor.py` performs exclusive copies only after validation. Dry-run never invokes filesystem mutations. There is no database or task queue.

## ADR 0002: Verify before unlinking

A plain rename could replace an existing file or fail across volumes. The executor uses exclusive target creation (`xb`), reads back and compares SHA-256 digests for the source and copied destination, and checks source identity before unlinking. This favors safety over raw speed; it is not an atomic transaction.

## ADR 0003: Versioned YAML without Pydantic

PyYAML `safe_load` plus small explicit validators is sufficient for this compact schema. Unknown keys and wrong types are rejected. A model framework would add a runtime dependency without much value at present.

## ADR 0004: JSON manifests for undo

A hidden destination-side manifest stores paths, status, and SHA-256 of successful moves. Undo validates roots, destinations, hashes and original path availability. Incomplete `planned` entries are not automatically reversed.

## ADR 0005: Stacked PRs and CI

PR #1: MVP; PR #2: YAML/recursion/exclusions; PR #3: manifests/undo; PR #4: documentation, demonstration and release readiness. They target their predecessor so `main` stays unchanged without explicit user approval. A single workflow runs Ruff, pytest, packaging and a real CLI demonstration on Python 3.14 across Ubuntu, Windows and macOS. Codex review happens only at the final gate.
