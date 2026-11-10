"""File operations with exclusive destination creation and rollback on failure."""

import os
import shutil
import stat
from contextlib import suppress

from fileflow.models import Move, MoveFailure, Plan, Result
from fileflow.planner import ensure_no_symlink_components, fingerprint


def _move_one(move: Move) -> None:
    """Copy first, verify source, then unlink. Never replace an existing target.

    Exclusive 'xb' protects against target creation between planning and execution.
    This is not a transactional operation or safe against malicious concurrent
    directory swaps; see README's documented limitations.
    """
    created = False
    target = move.destination
    try:
        before = move.source.lstat()
        if not stat.S_ISREG(before.st_mode) or fingerprint(before) != move.fingerprint:
            raise RuntimeError("Source changed after planning")

        ensure_no_symlink_components(target.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        ensure_no_symlink_components(target.parent)

        with move.source.open("rb") as reader:
            opened = os.fstat(reader.fileno())
            if fingerprint(opened) != move.fingerprint or not stat.S_ISREG(opened.st_mode):
                raise RuntimeError("Source changed while opening")
            with target.open("xb") as writer:
                created = True
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())

        after = move.source.lstat()
        if fingerprint(after) != move.fingerprint or not stat.S_ISREG(after.st_mode):
            raise RuntimeError("Source changed during copying")
        shutil.copystat(move.source, target, follow_symlinks=False)
        # Re-check before removing the source. A failed unlink leaves the original.
        latest = move.source.lstat()
        if fingerprint(latest) != move.fingerprint or not stat.S_ISREG(latest.st_mode):
            raise RuntimeError("Source changed before removal")
        move.source.unlink()
    except Exception:
        if created:
            # Preserve the original error, even if cleanup is denied.
            with suppress(OSError):
                target.unlink(missing_ok=True)
        raise


def execute_plan(plan: Plan) -> Result:
    """Execute independent operations and report failures without stopping the batch."""
    succeeded: list[Move] = []
    failed: list[MoveFailure] = []
    for move in plan.moves:
        try:
            _move_one(move)
            succeeded.append(move)
        except (OSError, RuntimeError, ValueError) as exc:
            failed.append(MoveFailure(move, str(exc)))
    return Result(tuple(succeeded), tuple(failed), plan.ignored)
