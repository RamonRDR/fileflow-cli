"""Persistent operation manifests and conflict-safe undo.

Each batch is persisted before the first copy. Successful moves are recorded
after the source is removed. Interrupted moves can leave a 'planned' entry;
those are deliberately not auto-recovered without a verified checksum.
"""

import json
import os
import re
import shutil
import stat
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fileflow.executor import _move_one, sha256_file
from fileflow.models import Move, MoveFailure, Plan, Result
from fileflow.planner import ensure_no_symlink_components, fingerprint, validate_roots

SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 10_000_000
MAX_ERROR_BYTES = 256
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
STATES = {"planned", "moved", "failed", "undone"}


@dataclass(frozen=True, slots=True)
class RecordedRun:
    """Execution result with an optional persistent manifest."""

    result: Result
    manifest: Path | None


@dataclass(frozen=True, slots=True)
class UndoReport:
    """Undo counters and descriptive conflicts/errors."""

    planned: int
    undone: int
    skipped: int
    conflicts: tuple[str, ...]
    failed: tuple[str, ...]


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _compact_error(error: str) -> str:
    """Bound journal error messages to avoid unexpected manifest growth."""
    return error.encode("utf-8", errors="replace")[:MAX_ERROR_BYTES].decode(
        "utf-8", errors="ignore"
    )


def _preflight_manifest_size(state: dict) -> None:
    """Reject oversized batches before creating a manifest or moving a source.

    Reserve the worst possible serialized growth per operation: successful
    moves may add a checksum and two timestamps, while failed operations may
    store an error. JSON can escape a single error byte as six ASCII characters.
    """
    timestamp = "9999-12-31T23:59:59.999999+00:00"
    worst_case = {
        **state,
        "operations": [
            {
                **entry,
                "status": "undone",
                "sha256": "0" * 64,
                "moved_at": timestamp,
                "undone_at": timestamp,
                "error": "x" * (6 * MAX_ERROR_BYTES),
            }
            for entry in state["operations"]
        ],
    }
    estimated_bytes = len(json.dumps(worst_case, ensure_ascii=False, indent=2).encode("utf-8")) + 1
    if estimated_bytes > MAX_MANIFEST_BYTES:
        raise ValueError(
            "Batch exceeds the 10 MB operation manifest limit; split the files "
            "into smaller batches. No files have been moved."
        )


def _dump(path: Path, data: dict, *, create: bool = False) -> None:
    """Persist JSON with fsync; changes to existing manifests use atomic replace."""
    ensure_no_symlink_components(path.parent)
    if create:
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            # First manifest write cannot have moved a file yet.
            raise
        return

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".fileflow-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def execute_recorded(plan: Plan, source: Path, destination: Path) -> RecordedRun:
    """Run a plan with a durable per-operation manifest, without overwriting files."""
    source_root, destination_root = validate_roots(source, destination)
    if not plan.moves:
        return RecordedRun(Result((), (), plan.ignored), None)

    state: dict = {
        "version": SCHEMA_VERSION,
        "created_at": _timestamp(),
        "source_root": str(source_root),
        "destination_root": str(destination_root),
        "operations": [
            {
                "source": str(move.source),
                "destination": str(move.destination),
                "status": "planned",
                "size": move.fingerprint[2],
                "sha256": None,
            }
            for move in plan.moves
        ],
    }
    _preflight_manifest_size(state)
    folder = destination_root / ".fileflow" / "manifests"
    ensure_no_symlink_components(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ensure_no_symlink_components(folder)
    manifest = folder / f"{uuid4().hex}.json"
    _dump(manifest, state, create=True)

    moved: list[Move] = []
    failed: list[MoveFailure] = []
    for move, entry in zip(plan.moves, state["operations"], strict=True):
        try:
            digest = _move_one(move)
        except (OSError, RuntimeError, ValueError) as exc:
            reason = _compact_error(str(exc))
            entry["status"] = "failed"
            entry["error"] = reason
            failed.append(MoveFailure(move, reason))
        else:
            entry["status"] = "moved"
            entry["sha256"] = digest
            entry["moved_at"] = _timestamp()
            moved.append(move)
        try:
            _dump(manifest, state)
        except OSError as exc:
            raise RuntimeError(
                f"Failed to update manifest {manifest}; inspect files before retrying: {exc}"
            ) from exc
    return RecordedRun(Result(tuple(moved), tuple(failed), plan.ignored), manifest)


def _read(path: Path) -> dict:
    input_path = Path(os.path.abspath(os.path.expanduser(os.fspath(path))))
    if input_path.is_symlink():
        raise ValueError("Manifest path cannot be a symbolic link")
    path = input_path.resolve(strict=False)
    ensure_no_symlink_components(path)
    if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError(f"Missing, invalid, or oversized manifest: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read operation manifest: {exc}") from exc
    if not isinstance(state, dict) or type(state.get("version")) is not int:
        raise ValueError("Invalid manifest schema")
    if state["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported manifest schema version")
    if not isinstance(state.get("source_root"), str) or not isinstance(
        state.get("destination_root"), str
    ):
        raise ValueError("Manifest roots must be strings")
    source_root = Path(state["source_root"])
    destination_root = Path(state["destination_root"])
    if not source_root.is_absolute() or not destination_root.is_absolute():
        raise ValueError("Manifest must store absolute root paths")
    checked_source, checked_destination = validate_roots(
        source_root, destination_root, require_source=False
    )
    if checked_source != source_root or checked_destination != destination_root:
        raise ValueError("Manifest root paths changed since the original run")
    expected = destination_root / ".fileflow" / "manifests"
    if path.parent != expected or path.suffix != ".json":
        raise ValueError("Manifest must live in the destination .fileflow/manifests directory")
    entries = state.get("operations")
    if not isinstance(entries, list):
        raise ValueError("Manifest operations must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid manifest operation")
        src = entry.get("source")
        dst = entry.get("destination")
        status = entry.get("status")
        checksum = entry.get("sha256")
        size = entry.get("size")
        if (
            not isinstance(src, str)
            or not isinstance(dst, str)
            or not isinstance(status, str)
            or status not in STATES
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("Invalid manifest operation fields")
        src_path, dst_path = Path(src), Path(dst)
        if (
            not src_path.is_absolute()
            or not dst_path.is_absolute()
            or Path(os.path.abspath(src)) != src_path
            or Path(os.path.abspath(dst)) != dst_path
            or src_path == source_root
            or dst_path == destination_root
            or source_root not in src_path.parents
            or destination_root not in dst_path.parents
        ):
            raise ValueError("Manifest operation escapes its declared roots")
        if status in {"moved", "undone"} and (
            not isinstance(checksum, str) or DIGEST.fullmatch(checksum) is None
        ):
            raise ValueError("Moved entries require a valid SHA-256 digest")
    return state


def _undo_one(source: Path, destination: Path, checksum: str, size: int) -> None:
    """Restore with exclusive create, verify copy, then remove the moved version."""
    if source.exists() or source.is_symlink():
        raise FileExistsError(f"Original path already exists: {source}")
    ensure_no_symlink_components(source.parent)
    ensure_no_symlink_components(destination)
    current = destination.lstat()
    if not stat.S_ISREG(current.st_mode) or current.st_size != size:
        raise RuntimeError(f"Moved file is missing or changed: {destination}")
    if sha256_file(destination) != checksum:
        raise RuntimeError(f"Moved file content was modified: {destination}")

    created = False
    try:
        source.parent.mkdir(parents=True, exist_ok=True)
        ensure_no_symlink_components(source.parent)
        with destination.open("rb") as reader, source.open("xb") as writer:
            created = True
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        if sha256_file(source) != checksum:
            raise RuntimeError("Restored copy failed integrity verification")
        if fingerprint(destination.lstat()) != fingerprint(current):
            raise RuntimeError("Moved file changed during undo")
        shutil.copystat(destination, source, follow_symlinks=False)
        destination.unlink()
    except Exception:
        if created:
            # Never mask the first error; a partial copy may need attention.
            with suppress(OSError):
                source.unlink(missing_ok=True)
        raise


def undo_manifest(path: Path, *, dry_run: bool = False) -> UndoReport:
    """Undo recorded moves without replacing existing source paths.

    Failed and uncommitted ('planned') entries are not undoable: a crash during
    moving may require manual reconciliation to avoid deleting unrelated files.
    """
    state = _read(path)
    manifest = Path(os.path.abspath(os.path.expanduser(os.fspath(path)))).resolve(strict=False)
    count = 0
    undone = 0
    skipped = 0
    conflicts: list[str] = []
    failures: list[str] = []
    for entry in reversed(state["operations"]):
        if entry["status"] != "moved":
            skipped += 1
            continue
        count += 1
        source = Path(entry["source"])
        destination = Path(entry["destination"])
        try:
            if dry_run:
                if source.exists() or source.is_symlink():
                    raise FileExistsError(f"Original path already exists: {source}")
                ensure_no_symlink_components(source.parent)
                ensure_no_symlink_components(destination)
                info = destination.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size != entry["size"]:
                    raise RuntimeError(f"Moved file is missing or changed: {destination}")
                if sha256_file(destination) != entry["sha256"]:
                    raise RuntimeError(f"Moved file content was modified: {destination}")
            else:
                _undo_one(source, destination, entry["sha256"], entry["size"])
                entry["status"] = "undone"
                entry["undone_at"] = _timestamp()
                _dump(manifest, state)
                undone += 1
        except (FileExistsError, ValueError, RuntimeError) as exc:
            conflicts.append(str(exc))
        except OSError as exc:
            failures.append(f"{source}: {exc}")
    return UndoReport(count, undone, skipped, tuple(conflicts), tuple(failures))
