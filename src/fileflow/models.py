"""Immutable planning and execution models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SortMode(str, Enum):
    """Available grouping strategies."""

    extension = "extension"
    category = "category"


@dataclass(frozen=True, slots=True)
class Move:
    """A proposed move and the source fingerprint recorded when it was planned."""

    source: Path
    destination: Path
    fingerprint: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class Plan:
    """A read-only plan. Constructing it must never touch the filesystem."""

    moves: tuple[Move, ...]
    ignored: int


@dataclass(frozen=True, slots=True)
class MoveFailure:
    """A failed operation, with a readable explanation."""

    move: Move
    reason: str


@dataclass(frozen=True, slots=True)
class Result:
    """Outcome of an execution, including partial failures."""

    moved: tuple[Move, ...]
    failed: tuple[MoveFailure, ...]
    ignored: int
