"""Recursive traversal and safe exclusion behavior."""

import pytest

from fileflow.executor import execute_plan
from fileflow.planner import build_plan


def test_recursive_flattens_nested_files_with_safe_collisions(folders):
    source, destination = folders
    (source / "one").mkdir()
    (source / "two").mkdir()
    (source / "one" / "same.txt").write_text("one", encoding="utf-8")
    (source / "two" / "same.txt").write_text("two", encoding="utf-8")

    plan = build_plan(source, destination, recursive=True)
    assert sorted(x.destination.name for x in plan.moves) == ["same (1).txt", "same.txt"]
    result = execute_plan(plan)
    assert not result.failed
    assert sorted(path.read_text(encoding="utf-8") for path in (destination / "txt").iterdir()) == [
        "one",
        "two",
    ]


def test_excluded_directory_is_not_traversed(folders):
    source, destination = folders
    (source / "cache").mkdir()
    (source / "cache" / "secret.txt").write_text("do not move", encoding="utf-8")
    (source / "valid.txt").write_text("move me", encoding="utf-8")
    plan = build_plan(source, destination, recursive=True, exclude_patterns=("cache/**",))
    assert [move.source.name for move in plan.moves] == ["valid.txt"]
    assert plan.ignored == 1
    result = execute_plan(plan)
    assert not result.failed
    assert (source / "cache" / "secret.txt").exists()


def test_single_file_glob_and_relative_path_glob(folders):
    source, destination = folders
    (source / "keep").mkdir()
    (source / "skip").mkdir()
    (source / "keep" / "keep.log").write_text("move", encoding="utf-8")
    (source / "keep" / "skip.tmp").write_text("ignore", encoding="utf-8")
    (source / "skip" / "secret.log").write_text("ignore", encoding="utf-8")
    plan = build_plan(
        source, destination, recursive=True, exclude_patterns=("*.tmp", "skip/**")
    )
    assert [move.source.name for move in plan.moves] == ["keep.log"]
    assert plan.ignored == 2


def test_recursive_never_follows_directory_symlink(folders):
    source, destination = folders
    outside = source.parent / "elsewhere"
    outside.mkdir()
    (outside / "private.txt").write_text("private", encoding="utf-8")
    try:
        (source / "shortcut").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not available")
    plan = build_plan(source, destination, recursive=True)
    assert plan.moves == ()
    assert plan.ignored == 1
    assert not destination.exists()


def test_hidden_directories_not_traversed(folders):
    source, destination = folders
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("ignore", encoding="utf-8")
    assert build_plan(source, destination, recursive=True).ignored == 1
    assert not destination.exists()


@pytest.mark.parametrize("pattern", ["../escape", "/absolute", r"C:\escape", "", "foo/../bar"])
def test_invalid_exclusion_patterns_rejected(folders, pattern):
    source, destination = folders
    with pytest.raises(ValueError, match="exclusion"):
        build_plan(source, destination, exclude_patterns=(pattern,))
