"""Built-in categories and validated CLI overrides."""

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from fileflow.models import SortMode

DEFAULT_CATEGORIES: dict[str, frozenset[str]] = {
    "Documents": frozenset({".pdf", ".doc", ".docx", ".txt", ".md", ".csv", ".xlsx", ".pptx"}),
    "Images": frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic"}),
    "Videos": frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm"}),
    "Archives": frozenset({".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tar.bz2", ".gz"}),
    "Audio": frozenset({".mp3", ".wav", ".flac", ".ogg"}),
}

_CATEGORY_RE = re.compile(r"[A-Za-z][A-Za-z0-9 _-]{0,39}\Z")
_EXTENSION_RE = re.compile(r"\.[a-z0-9][a-z0-9_+-]*(?:\.[a-z0-9][a-z0-9_+-]*)*\Z")
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                     *(f"LPT{i}" for i in range(1, 10))}


def parse_categories(overrides: Sequence[str]) -> dict[str, frozenset[str]]:
    """Overlay custom CATEGORY=.ext,.ext rules onto built-in categories.

    An explicitly assigned extension wins over a default assignment. Two explicit
    assignments for the same extension are rejected instead of depending on order.
    """
    custom: dict[str, set[str]] = {}
    assigned: set[str] = set()
    for raw in overrides:
        name, sep, extensions = raw.partition("=")
        name = name.strip()
        if not sep or not _CATEGORY_RE.fullmatch(name) or name.rstrip(" .") != name:
            raise ValueError(f"Invalid category rule {raw!r}; expected Name=.pdf,.txt")
        if name.upper() in _WINDOWS_RESERVED:
            raise ValueError(f"Reserved category name: {name}")
        values = [item.strip().casefold() for item in extensions.split(",")]
        if not values or any(not _EXTENSION_RE.fullmatch(value) for value in values):
            raise ValueError(f"Invalid extensions in {raw!r}; use .pdf,.txt")
        for value in values:
            if value in assigned:
                raise ValueError(f"Extension {value!r} appears in multiple custom rules")
            assigned.add(value)
            custom.setdefault(name, set()).add(value)

    result = {name: set(values) - assigned for name, values in DEFAULT_CATEGORIES.items()}
    for name, values in custom.items():
        result.setdefault(name, set()).update(values)
    return {name: frozenset(values) for name, values in result.items()}


def file_extension(path: Path, categories: Mapping[str, frozenset[str]]) -> str:
    """Recognize configured compound extensions before falling back to suffix."""
    filename = path.name.casefold()
    known = sorted({ext for values in categories.values() for ext in values},
                   key=len, reverse=True)
    for extension in known:
        if filename.endswith(extension) and len(filename) > len(extension):
            return extension
    return path.suffix.casefold()


def destination_group(
    path: Path, mode: SortMode, categories: Mapping[str, frozenset[str]]
) -> str:
    """Return a safe subdirectory name for an extension or category."""
    extension = file_extension(path, categories)
    if mode is SortMode.extension:
        return extension.removeprefix(".") if extension else "no-extension"
    for name, extensions in categories.items():
        if extension in extensions:
            return name
    return "Other"
