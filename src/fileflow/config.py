"""Small, strict YAML configuration loader without runtime model dependencies."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from fileflow.models import SortMode
from fileflow.rules import parse_categories, validate_exclusions


@dataclass(frozen=True, slots=True)
class Settings:
    """Settings loaded from a trusted, local configuration file."""

    mode: SortMode = SortMode.extension
    by_date: bool = False
    recursive: bool = False
    category_rules: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()


def _read_categories(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        raise ValueError("categories must be a mapping of names to lists of extensions")
    overrides: list[str] = []
    for name, items in value.items():
        if not isinstance(name, str) or not isinstance(items, list):
            raise ValueError("categories must map a name to a list of extensions")
        if not items or any(not isinstance(item, str) for item in items):
            raise ValueError("Each category must contain one or more string extensions")
        overrides.append(f"{name}={','.join(items)}")
    parse_categories(overrides)
    return tuple(overrides)


def load_config(path: Path) -> Settings:
    """Load a versioned YAML file, rejecting unknown keys and unsafe types.

    YAML is parsed with safe_load: Python objects and arbitrary constructors
    are never deserialized.
    """
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Config must be an existing regular file, not a symlink: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Cannot read YAML configuration: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a YAML mapping")
    keys = {"version", "mode", "by_date", "recursive", "categories", "exclude"}
    unknown = set(raw) - keys
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(map(str, unknown))}")
    if type(raw.get("version")) is not int or raw["version"] != 1:
        raise ValueError("Configuration requires version: 1")
    try:
        mode = SortMode(raw.get("mode", "extension"))
    except ValueError as exc:
        raise ValueError("mode must be extension or category") from exc
    by_date = raw.get("by_date", False)
    recursive = raw.get("recursive", False)
    if not isinstance(by_date, bool) or not isinstance(recursive, bool):
        raise ValueError("by_date and recursive must be booleans")
    categories = _read_categories(raw.get("categories", {}))
    exclusions = raw.get("exclude", [])
    if not isinstance(exclusions, list) or any(not isinstance(x, str) for x in exclusions):
        raise ValueError("exclude must be a list of glob pattern strings")
    return Settings(
        mode=mode,
        by_date=by_date,
        recursive=recursive,
        category_rules=categories,
        exclude=validate_exclusions(exclusions),
    )
