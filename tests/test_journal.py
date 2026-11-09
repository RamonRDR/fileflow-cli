"""Operation manifests and conflict-safe undo using disposable pytest paths."""

import json

import pytest
from typer.testing import CliRunner

from fileflow.cli import app
from fileflow.journal import execute_recorded, undo_manifest
from fileflow.planner import build_plan

runner = CliRunner()


def _record(folders):
    source, destination = folders
    (source / "report.txt").write_text("original content", encoding="utf-8")
    record = execute_recorded(build_plan(source, destination), source, destination)
    assert record.manifest is not None
    return record


def test_recorded_move_manifest_and_undo_round_trip(folders):
    source, destination = folders
    record = _record(folders)
    assert len(record.result.moved) == 1
    path = destination / "txt" / "report.txt"
    assert path.read_text(encoding="utf-8") == "original content"
    assert not (source / "report.txt").exists()

    data = json.loads(record.manifest.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["operations"][0]["status"] == "moved"
    assert len(data["operations"][0]["sha256"]) == 64

    preview = undo_manifest(record.manifest, dry_run=True)
    assert preview.planned == 1
    assert preview.undone == 0
    assert not preview.conflicts
    assert not (source / "report.txt").exists()

    done = undo_manifest(record.manifest)
    assert done.undone == 1
    assert not done.conflicts
    assert (source / "report.txt").read_text(encoding="utf-8") == "original content"
    assert not path.exists()

    again = undo_manifest(record.manifest)
    assert again.planned == 0
    assert again.skipped == 1
    assert again.undone == 0
    assert (
        json.loads(record.manifest.read_text(encoding="utf-8"))["operations"][0]["status"]
        == "undone"
    )


def test_undo_never_overwrites_original_name(folders):
    source, destination = folders
    record = _record(folders)
    (source / "report.txt").write_text("new personal file", encoding="utf-8")
    result = undo_manifest(record.manifest)
    assert result.undone == 0
    assert len(result.conflicts) == 1
    assert (source / "report.txt").read_text(encoding="utf-8") == "new personal file"
    assert (destination / "txt" / "report.txt").read_text(encoding="utf-8") == "original content"


def test_modified_destination_is_never_undone(folders):
    source, destination = folders
    record = _record(folders)
    changed = destination / "txt" / "report.txt"
    changed.write_text("modified content", encoding="utf-8")
    result = undo_manifest(record.manifest)
    assert result.undone == 0
    assert len(result.conflicts) == 1
    assert changed.read_text(encoding="utf-8") == "modified content"
    assert not (source / "report.txt").exists()


def test_missing_destination_is_reported_without_restore(folders):
    source, destination = folders
    record = _record(folders)
    moved = destination / "txt" / "report.txt"
    moved.unlink()
    result = undo_manifest(record.manifest)
    assert result.undone == 0
    assert len(result.failed) == 1
    assert not (source / "report.txt").exists()


def test_manifest_tampered_to_escape_roots_is_rejected(folders):
    source, destination = folders
    record = _record(folders)
    state = json.loads(record.manifest.read_text(encoding="utf-8"))
    state["operations"][0]["source"] = str(source.parent / "external.txt")
    record.manifest.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        undo_manifest(record.manifest)
    assert (destination / "txt" / "report.txt").exists()


def test_manifest_traversal_with_dotdot_is_rejected(folders):
    source, destination = folders
    record = _record(folders)
    state = json.loads(record.manifest.read_text(encoding="utf-8"))
    state["operations"][0]["source"] = str(source / ".." / "external.txt")
    record.manifest.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        undo_manifest(record.manifest)
    assert (destination / "txt" / "report.txt").exists()


def test_invalid_json_is_rejected(folders):
    record = _record(folders)
    record.manifest.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Cannot read"):
        undo_manifest(record.manifest)


def test_empty_plan_creates_no_manifest_or_destination(folders):
    source, destination = folders
    recorded = execute_recorded(build_plan(source, destination), source, destination)
    assert recorded.manifest is None
    assert not destination.exists()


def test_partial_move_failure_is_logged_and_other_moves_continue(folders, monkeypatch):
    source, destination = folders
    (source / "a.txt").write_text("first", encoding="utf-8")
    (source / "b.txt").write_text("second", encoding="utf-8")
    plan = build_plan(source, destination)
    original = __import__("fileflow.journal", fromlist=["_move_one"])._move_one

    def fail_one(move):
        if move.source.name == "a.txt":
            raise PermissionError("simulated locked file")
        return original(move)

    monkeypatch.setattr("fileflow.journal._move_one", fail_one)
    record = execute_recorded(plan, source, destination)
    assert len(record.result.failed) == 1
    assert len(record.result.moved) == 1
    data = json.loads(record.manifest.read_text(encoding="utf-8"))
    assert [item["status"] for item in data["operations"]] == ["failed", "moved"]
    assert (source / "a.txt").exists()
    assert (destination / "txt" / "b.txt").exists()
    restored = undo_manifest(record.manifest)
    assert restored.undone == 1
    assert restored.skipped == 1
    assert (source / "b.txt").exists()


def test_failed_initial_manifest_write_keeps_source(folders, monkeypatch):
    source, destination = folders
    original = source / "report.txt"
    original.write_text("original", encoding="utf-8")

    def denied(*args, **kwargs):
        raise PermissionError("journal inaccessible")

    monkeypatch.setattr("fileflow.journal._dump", denied)
    with pytest.raises(PermissionError, match="journal inaccessible"):
        execute_recorded(build_plan(source, destination), source, destination)
    assert original.read_text(encoding="utf-8") == "original"
    assert not (destination / "txt" / "report.txt").exists()


def test_undo_copy_failure_leaves_moved_file(folders, monkeypatch):
    source, destination = folders
    record = _record(folders)

    def denied(*args, **kwargs):
        raise PermissionError("simulated copy error")

    monkeypatch.setattr("fileflow.journal.shutil.copyfileobj", denied)
    report = undo_manifest(record.manifest)
    assert report.undone == 0
    assert len(report.failed) == 1
    assert not (source / "report.txt").exists()
    assert (destination / "txt" / "report.txt").exists()


def test_cli_undo_dry_run_then_execute(folders):
    source, destination = folders
    (source / "sample.pdf").write_bytes(b"sample")
    organized = runner.invoke(app, ["organize", str(source), "-d", str(destination)])
    assert organized.exit_code == 0, organized.output
    manifests = list((destination / ".fileflow" / "manifests").glob("*.json"))
    assert len(manifests) == 1
    first = runner.invoke(app, ["undo", str(manifests[0]), "--dry-run"])
    assert first.exit_code == 0, first.output
    assert not (source / "sample.pdf").exists()
    second = runner.invoke(app, ["undo", str(manifests[0])])
    assert second.exit_code == 0, second.output
    assert (source / "sample.pdf").read_bytes() == b"sample"


def test_cli_undo_conflict_has_nonzero_exit(folders):
    source, destination = folders
    record = _record(folders)
    (source / "report.txt").write_text("new", encoding="utf-8")
    result = runner.invoke(app, ["undo", str(record.manifest)])
    assert result.exit_code == 1
    assert "CONFLICT" in result.output


def test_undo_refuses_symlink_original(folders):
    source, destination = folders
    record = _record(folders)
    outside = source.parent / "external.txt"
    outside.write_text("untouched", encoding="utf-8")
    try:
        (source / "report.txt").symlink_to(outside)
    except OSError, NotImplementedError:
        pytest.skip("Symlinks not available")
    result = undo_manifest(record.manifest)
    assert len(result.conflicts) == 1
    assert outside.read_text(encoding="utf-8") == "untouched"
    assert (destination / "txt" / "report.txt").exists()


def test_undo_recreates_deleted_source_root_without_mutating_dry_run(folders):
    source, destination = folders
    record = _record(folders)
    source.rmdir()
    assert not source.exists()

    preview = undo_manifest(record.manifest, dry_run=True)
    assert preview.planned == 1
    assert preview.undone == 0
    assert not preview.conflicts
    assert not source.exists()

    restored = undo_manifest(record.manifest)
    assert restored.undone == 1
    assert not restored.conflicts
    assert (source / "report.txt").read_text(encoding="utf-8") == "original content"
    assert not (destination / "txt" / "report.txt").exists()


def test_undo_rejects_replaced_source_root_file(folders):
    source, destination = folders
    record = _record(folders)
    source.rmdir()
    source.write_text("not a folder", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        undo_manifest(record.manifest)
    assert source.read_text(encoding="utf-8") == "not a folder"
    assert (destination / "txt" / "report.txt").exists()


def test_undo_rejects_symlink_replacing_source_root(folders):
    source, destination = folders
    record = _record(folders)
    source.rmdir()
    external = source.parent / "external"
    external.mkdir()
    try:
        source.symlink_to(external, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("Directory symlinks not available")
    with pytest.raises(ValueError, match="Symbolic links"):
        undo_manifest(record.manifest)
    assert not (external / "report.txt").exists()
    assert (destination / "txt" / "report.txt").exists()


def test_oversized_batch_rejected_before_files_are_moved(folders, monkeypatch):
    source, destination = folders
    original = source / "important.txt"
    original.write_text("keep", encoding="utf-8")
    monkeypatch.setattr("fileflow.journal.MAX_MANIFEST_BYTES", 1000)

    with pytest.raises(ValueError, match="split the files"):
        execute_recorded(build_plan(source, destination), source, destination)
    assert original.read_text(encoding="utf-8") == "keep"
    assert not destination.exists()


def test_oversized_batch_cli_returns_input_error(folders, monkeypatch):
    source, destination = folders
    (source / "important.txt").write_text("keep", encoding="utf-8")
    monkeypatch.setattr("fileflow.journal.MAX_MANIFEST_BYTES", 1000)

    result = runner.invoke(app, ["organize", str(source), "-d", str(destination)])
    assert result.exit_code == 2
    assert "split the files" in result.output
    assert (source / "important.txt").exists()
    assert not destination.exists()


def test_bounded_error_keeps_written_manifest_readable(folders, monkeypatch):
    source, destination = folders
    (source / "a.txt").write_text("first", encoding="utf-8")
    (source / "b.txt").write_text("second", encoding="utf-8")
    monkeypatch.setattr("fileflow.journal.MAX_MANIFEST_BYTES", 5000)
    original_move = __import__("fileflow.journal", fromlist=["_move_one"])._move_one

    def long_failure(move):
        if move.source.name == "a.txt":
            raise RuntimeError("🧪" * 5000)
        return original_move(move)

    monkeypatch.setattr("fileflow.journal._move_one", long_failure)
    recorded = execute_recorded(build_plan(source, destination), source, destination)
    assert len(recorded.result.failed) == 1
    assert len(recorded.result.moved) == 1
    assert recorded.manifest.stat().st_size <= 5000
    status = json.loads(recorded.manifest.read_text(encoding="utf-8"))
    assert status["operations"][0]["status"] == "failed"
    assert len(status["operations"][0]["error"].encode("utf-8")) <= 256
    preview = undo_manifest(recorded.manifest, dry_run=True)
    assert preview.planned == 1
    assert not preview.conflicts
    assert (source / "a.txt").exists()
