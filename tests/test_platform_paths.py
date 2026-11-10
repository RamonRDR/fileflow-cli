"""Canonical path alias behavior on macOS and other operating systems."""

import pytest

from fileflow.journal import execute_recorded, undo_manifest
from fileflow.planner import build_plan


def _alias(tmp_path):
    link = tmp_path / "alias"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("Directory symlinks not available")
    return link


def test_ancestor_symlink_is_resolved_before_planning(folders):
    source, destination = folders
    (source / "safe.txt").write_text("safe", encoding="utf-8")
    link = _alias(source.parent)
    plan = build_plan(link / "inbox", destination)
    assert len(plan.moves) == 1
    assert plan.moves[0].source == (source / "safe.txt").resolve()
    assert plan.moves[0].destination.parent == destination.resolve() / "txt"


def test_direct_symlink_destination_root_is_rejected(folders):
    source, destination = folders
    destination.mkdir()
    link = _alias(source.parent)
    with pytest.raises(ValueError, match="Symbolic links"):
        build_plan(source, link)


def test_manifest_path_via_ancestor_alias_is_supported(folders):
    source, destination = folders
    (source / "safe.txt").write_text("hello", encoding="utf-8")
    run = execute_recorded(build_plan(source, destination), source, destination)
    link = _alias(source.parent)
    manifest_alias = link / "sorted" / ".fileflow" / "manifests" / run.manifest.name
    preview = undo_manifest(manifest_alias, dry_run=True)
    assert preview.planned == 1
    assert not preview.conflicts
    assert (destination / "txt" / "safe.txt").exists()
