"""Test fixtures are confined to pytest's disposable tmp_path."""

from pathlib import Path

import pytest


@pytest.fixture
def folders(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "inbox"
    destination = tmp_path / "sorted"
    source.mkdir()
    return source, destination
