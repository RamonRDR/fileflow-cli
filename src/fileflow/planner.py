"""Non-destructive validation and move planning."""

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from fileflow.models import Move, Plan, SortMode
from fileflow.rules import destination_group, excluded, parse_categories, validate_exclusions


def fingerprint(info: os.stat_result) -> tuple[int, int, int, int]:
    """Capture enough source metadata to detect common concurrent changes."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def ensure_no_symlink_components(path: Path) -> None:
    """Reject link-bearing input paths, including an existing ancestor."""
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError(f"Symbolic links in paths are not supported: {path}")


def validate_roots(
    source: Path, destination: Path, *, require_source: bool = True
) -> tuple[Path, Path]:
    """Validate non-overlapping roots; undo may restore a missing source directory."""
    input_source = Path(os.path.abspath(os.path.expanduser(os.fspath(source))))
    input_destination = Path(os.path.abspath(os.path.expanduser(os.fspath(destination))))
    # Reject directly selected link roots. Ancestor aliases such as macOS /var
    # are resolved to physical paths before planning and shown in the plan.
    if input_source.is_symlink() or input_destination.is_symlink():
        raise ValueError("Symbolic links are not accepted as source or destination roots")
    source = input_source.resolve(strict=False)
    destination = input_destination.resolve(strict=False)
    ensure_no_symlink_components(source)
    ensure_no_symlink_components(destination)

    source_exists = source.exists()
    if source_exists and not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")
    if require_source and not source_exists:
        raise ValueError(f"Source directory does not exist: {source}")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Destination is not a directory: {destination}")

    actual_source = source.resolve(strict=source_exists)
    actual_destination = destination.resolve(strict=False)
    if (
        actual_source == actual_destination
        or actual_source in actual_destination.parents
        or actual_destination in actual_source.parents
    ):
        raise ValueError("Source and destination must be separate, non-overlapping directories")

    if source_exists and not os.access(source, os.R_OK | os.X_OK):
        raise ValueError(f"Source directory cannot be read: {source}")

    writable_parent = destination
    while not writable_parent.exists():
        writable_parent = writable_parent.parent
    if not os.access(writable_parent, os.W_OK | os.X_OK):
        raise ValueError(f"Destination parent is not writable: {writable_parent}")
    return source, destination


def _available_path(requested: Path, taken: set[str]) -> Path:
    candidate = requested
    index = 1
    while str(candidate).casefold() in taken or candidate.exists() or candidate.is_symlink():
        candidate = requested.with_name(f"{requested.stem} ({index}){requested.suffix}")
        index += 1
    taken.add(str(candidate).casefold())
    return candidate


def _candidates(source: Path, *, recursive: bool, patterns: tuple[str, ...]):
    """Yield non-hidden, regular files without descending into links or excluded dirs."""
    folders = [source]
    while folders:
        folder = folders.pop()
        for path in sorted(folder.iterdir(), key=lambda item: (item.name.casefold(), item.name)):
            relative = path.relative_to(source).as_posix()
            if path.name.startswith(".") or path.is_symlink() or excluded(relative, patterns):
                yield path, None
                continue
            info = path.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                if recursive:
                    folders.append(path)
                else:
                    yield path, None
            elif stat.S_ISREG(info.st_mode):
                yield path, info
            else:
                yield path, None


def build_plan(
    source: Path,
    destination: Path,
    *,
    mode: SortMode = SortMode.extension,
    by_date: bool = False,
    category_rules: tuple[str, ...] = (),
    recursive: bool = False,
    exclude_patterns: tuple[str, ...] = (),
) -> Plan:
    """Discover files, applying strict roots, exclusions and deterministic naming."""
    source, destination = validate_roots(source, destination)
    categories = parse_categories(category_rules)
    patterns = validate_exclusions(exclude_patterns)
    if category_rules and mode is not SortMode.category:
        raise ValueError("--category or YAML categories requires --mode category")

    planned: list[Move] = []
    taken: set[str] = set()
    ignored = 0
    for path, info in _candidates(source, recursive=recursive, patterns=patterns):
        if info is None:
            ignored += 1
            continue
        grouping = destination_group(path, mode, categories)
        folder = destination / grouping
        if by_date:
            modified = datetime.fromtimestamp(info.st_mtime, tz=UTC)
            folder = folder / modified.strftime("%Y") / modified.strftime("%m")
        target = _available_path(folder / path.name, taken)
        planned.append(Move(path, target, fingerprint(info)))
    return Plan(tuple(planned), ignored)
