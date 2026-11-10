"""Execution tests never leave pytest's temporary directories."""

import pytest

from fileflow.executor import execute_plan
from fileflow.planner import build_plan


def test_move_by_extension_preserves_contents(folders):
    source, destination = folders
    original = source / "mañana 🐱.txt"
    original.write_text("unicode content", encoding="utf-8")
    result = execute_plan(build_plan(source, destination))
    assert len(result.moved) == 1
    assert result.failed == ()
    assert not original.exists()
    assert (destination / "txt" / original.name).read_text(encoding="utf-8") == "unicode content"


def test_existing_file_is_preserved(folders):
    source, destination = folders
    (source / "receipt.txt").write_text("new", encoding="utf-8")
    target_folder = destination / "txt"
    target_folder.mkdir(parents=True)
    (target_folder / "receipt.txt").write_text("original", encoding="utf-8")

    result = execute_plan(build_plan(source, destination))
    assert len(result.moved) == 1
    assert (target_folder / "receipt.txt").read_text(encoding="utf-8") == "original"
    assert (target_folder / "receipt (1).txt").read_text(encoding="utf-8") == "new"


def test_collision_created_after_planning_does_not_overwrite(folders):
    source, destination = folders
    original = source / "book.txt"
    original.write_text("from source", encoding="utf-8")
    plan = build_plan(source, destination)
    target = plan.moves[0].destination
    target.parent.mkdir(parents=True)
    target.write_text("already here", encoding="utf-8")
    result = execute_plan(plan)

    assert result.moved == ()
    assert len(result.failed) == 1
    assert original.read_text(encoding="utf-8") == "from source"
    assert target.read_text(encoding="utf-8") == "already here"


def test_source_changed_after_planning_is_not_moved(folders):
    source, destination = folders
    original = source / "report.txt"
    original.write_text("first", encoding="utf-8")
    plan = build_plan(source, destination)
    original.write_text("different content", encoding="utf-8")
    result = execute_plan(plan)

    assert len(result.failed) == 1
    assert result.moved == ()
    assert original.read_text(encoding="utf-8") == "different content"
    assert not (destination / "txt" / "report.txt").exists()


def test_copy_failure_keeps_source_and_cleans_target(folders, monkeypatch):
    source, destination = folders
    original = source / "portrait.png"
    original.write_bytes(b"picture")
    plan = build_plan(source, destination)

    def broken_copy(*args, **kwargs):
        raise PermissionError("simulated locked file")

    monkeypatch.setattr("fileflow.executor.shutil.copyfileobj", broken_copy)
    result = execute_plan(plan)
    assert len(result.failed) == 1
    assert "simulated locked file" in result.failed[0].reason
    assert original.read_bytes() == b"picture"
    assert not plan.moves[0].destination.exists()


def test_partial_failure_continues_with_next_file(folders):
    source, destination = folders
    first = source / "a.txt"
    second = source / "b.txt"
    first.write_text("old", encoding="utf-8")
    second.write_text("safe", encoding="utf-8")
    plan = build_plan(source, destination)
    first.write_text("modified since planning", encoding="utf-8")

    result = execute_plan(plan)
    assert len(result.failed) == 1
    assert len(result.moved) == 1
    assert first.exists()
    assert not second.exists()
    assert (destination / "txt" / "b.txt").read_text(encoding="utf-8") == "safe"


def test_destination_symlink_swap_is_rejected(folders):
    source, destination = folders
    (source / "message.txt").write_text("safe", encoding="utf-8")
    plan = build_plan(source, destination)
    outside = source.parent / "outside"
    outside.mkdir()
    destination.mkdir()
    try:
        (destination / "txt").symlink_to(outside, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("Directory symlinks unavailable")

    result = execute_plan(plan)
    assert len(result.failed) == 1
    assert (source / "message.txt").exists()
    assert not (outside / "message.txt").exists()


def test_corrupted_copy_preserves_source_and_removes_new_target(folders, monkeypatch):
    source, destination = folders
    original = source / "important.txt"
    original.write_bytes(b"good")
    plan = build_plan(source, destination)

    def corrupted_copy(reader, writer, length):
        writer.write(b"bad!")  # Same size; metadata alone would not detect corruption.

    monkeypatch.setattr("fileflow.executor.shutil.copyfileobj", corrupted_copy)
    result = execute_plan(plan)

    assert result.moved == ()
    assert len(result.failed) == 1
    assert "differs from source" in result.failed[0].reason
    assert original.read_bytes() == b"good"
    assert not plan.moves[0].destination.exists()
