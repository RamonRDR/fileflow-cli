"""Planning tests verify no real files are moved or created."""

import os
from datetime import UTC, datetime

import pytest

from fileflow.models import SortMode
from fileflow.planner import build_plan


def test_plan_is_read_only(folders):
    source, destination = folders
    original = source / "résumé ✨.PDF"
    original.write_text("safe", encoding="utf-8")
    plan = build_plan(source, destination)
    assert len(plan.moves) == 1
    assert plan.moves[0].destination == destination / "pdf" / original.name
    assert original.read_text(encoding="utf-8") == "safe"
    assert not destination.exists()


def test_ignores_hidden_entries_directories_and_symlinks(folders):
    source, destination = folders
    (source / ".env").write_text("pretend secret", encoding="utf-8")
    (source / "folder").mkdir()
    (source / "ok.txt").write_text("hello", encoding="utf-8")
    symlink = source / "alias.txt"
    try:
        symlink.symlink_to(source / "ok.txt")
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable in this test environment")
    plan = build_plan(source, destination)
    assert [move.source.name for move in plan.moves] == ["ok.txt"]
    assert plan.ignored == 3


def test_empty_directory_is_valid(folders):
    source, destination = folders
    plan = build_plan(source, destination)
    assert plan.moves == ()
    assert plan.ignored == 0
    assert not destination.exists()


def test_missing_extension_is_grouped(folders):
    source, destination = folders
    (source / "LICENSE").write_text("example", encoding="utf-8")
    plan = build_plan(source, destination)
    assert plan.moves[0].destination == destination / "no-extension" / "LICENSE"


def test_category_mode_custom_rules(folders):
    source, destination = folders
    (source / "paper.pdf").write_text("paper", encoding="utf-8")
    plan = build_plan(source, destination, mode=SortMode.category,
                      category_rules=("Research=.pdf",))
    assert plan.moves[0].destination == destination / "Research" / "paper.pdf"


def test_month_folders_are_based_on_utc_mtime(folders):
    source, destination = folders
    file = source / "holiday.png"
    file.write_bytes(b"png")
    moment = datetime(2024, 12, 31, 23, 0, tzinfo=UTC).timestamp()
    os.utime(file, (moment, moment))
    plan = build_plan(source, destination, by_date=True)
    assert plan.moves[0].destination == destination / "png" / "2024" / "12" / "holiday.png"


def test_existing_name_is_not_reused(folders):
    source, destination = folders
    (source / "invoice.txt").write_text("new", encoding="utf-8")
    (destination / "txt").mkdir(parents=True)
    (destination / "txt" / "invoice.txt").write_text("old", encoding="utf-8")
    (destination / "txt" / "invoice (1).txt").write_text("older", encoding="utf-8")
    plan = build_plan(source, destination)
    assert plan.moves[0].destination.name == "invoice (2).txt"


@pytest.mark.parametrize("destination_kind", ["same", "child", "parent"])
def test_overlap_is_rejected(tmp_path, destination_kind):
    source = tmp_path / "work" / "inbox"
    source.mkdir(parents=True)
    destinations = {
        "same": source,
        "child": source / "sorted",
        "parent": source.parent,
    }
    with pytest.raises(ValueError, match="non-overlapping"):
        build_plan(source, destinations[destination_kind])


def test_missing_source_rejected(folders):
    source, destination = folders
    with pytest.raises(ValueError, match="does not exist"):
        build_plan(source / "not-here", destination)


def test_destination_file_rejected(folders):
    source, destination = folders
    destination.write_text("not a folder", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        build_plan(source, destination)


def test_source_symlink_rejected(folders):
    source, destination = folders
    link = source.parent / "linked"
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks unavailable")
    with pytest.raises(ValueError, match="Symbolic links"):
        build_plan(link, destination)


def test_unreadable_source_rejected(folders, monkeypatch):
    source, destination = folders
    monkeypatch.setattr("fileflow.planner.os.access", lambda path, mode: path != source)
    with pytest.raises(ValueError, match="cannot be read"):
        build_plan(source, destination)


def test_custom_category_requires_category_mode(folders):
    source, destination = folders
    with pytest.raises(ValueError, match="requires"):
        build_plan(source, destination, category_rules=("Research=.pdf",))
