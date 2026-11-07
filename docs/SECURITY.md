# Security model and operating limitations

FileFlow is designed to reduce **accidental local file loss**, not to be a hardened sandbox for hostile concurrent access.

## Invariants and mechanisms

| Risk | Mitigation |
| --- | --- |
| Same or nested roots | Reject both nesting directions after canonical resolution; reject terminal symlink roots while normalizing ancestor aliases (e.g. macOS /var) |
| Following links | Ignore link entries and hidden folders; reject symlink-bearing destination parents |
| Existing output gets replaced | Plan numbered destinations and open with exclusive `xb` |
| Source removed before copy | Complete copy, fsync, compare source and destination SHA-256, and recheck metadata before unlinking source |
| Interrupted/failed copy | Leave original; attempt to delete only this operation's newly created target |
| Missing audit history | Persist a unique per-run manifest before the first move; update success/failure after each operation |
| Undo overwrites original | Restore using exclusive `xb` and fail if source exists or is a symlink |
| Undo destroys changed target | Verify destination size and SHA-256 before copying back and unlinking |
| Test modifies real data | All mutating tests use pytest `tmp_path`; the demo uses `TemporaryDirectory` |

## Journal semantics

Manifests reside at `<destination>/.fileflow/manifests/<uuid>.json` and contain absolute paths, status, size and SHA-256 for successful movements. A batch with zero candidate files does not create a manifest. Updates use a temporary file in the same directory followed by `os.replace`. Undo changes `moved` entries to `undone` after successfully restoring the original.

A process may die after source removal but before its next manifest update, leaving `planned` even though the destination has data. **Do not blindly retry or delete anything.** That entry requires manual inspection. Undo intentionally skips `planned` and `failed` entries. A failed manifest update interrupts processing and prints the path for investigation. An update failure after undo can leave a restored file while the manifest still says `moved`; another undo reports a conflict rather than overwriting it.

## Threat-model exclusions

- Copy-then-unlink is **not atomic** across devices or even within one filesystem.
- There is a time-of-check/time-of-use window around path validation and file opens. Malicious concurrent directory changes are not fully defended against.
- Power failure can leave a partial file or an incomplete journal; durable directory fsync is not guaranteed on every platform.
- Source identity checks use stat information and can miss adversarial changes preserving those attributes.
- Manifests are **trusted local data**. Do not load them from unknown sources; they also reveal local directory names.
- Network filesystems, concurrent organizers, and filesystem-specific ACL semantics are outside tested guarantees.
- Case and collision handling can differ by filesystem even though planning compares destinations case-insensitively.

## Operational recommendations

Back up irreplaceable data. Start with `fileflow organize ... --dry-run`, inspect the plan, run on disposable samples, and keep the printed manifest path. Before undo, run `fileflow undo ... --dry-run` and inspect conflicts. Never place destination inside source or vice versa.

For reproducible safety tests use `python -m pytest -q`. No test fixture may reference a user's home, Downloads, or Desktop as its write target.
