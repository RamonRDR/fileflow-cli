"""Exercise the public CLI, not only its internal helpers."""

from click.utils import strip_ansi
from typer.testing import CliRunner

from fileflow.cli import app

runner = CliRunner()


def test_help_mentions_safety_controls():
    result = runner.invoke(app, ["organize", "--help"])
    assert result.exit_code == 0
    help_text = strip_ansi(result.output)
    assert "--dry-run" in help_text
    assert "--destination" in help_text
    assert "--category" in help_text


def test_dry_run_does_not_create_destination(folders):
    source, destination = folders
    original = source / "draft.md"
    original.write_text("draft", encoding="utf-8")
    result = runner.invoke(
        app, ["organize", str(source), "--destination", str(destination), "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "1 planned" in result.output
    assert original.exists()
    assert not destination.exists()


def test_cli_organizes_by_category(folders):
    source, destination = folders
    (source / "chart.png").write_bytes(b"fake-png")
    result = runner.invoke(
        app, ["organize", str(source), "-d", str(destination), "--mode", "category"]
    )
    assert result.exit_code == 0, result.output
    assert "1 moved" in result.output
    assert (destination / "Images" / "chart.png").exists()


def test_cli_invalid_path_exits_two(folders):
    source, destination = folders
    result = runner.invoke(app, ["organize", str(source / "missing"), "-d", str(destination)])
    assert result.exit_code == 2
    assert "Cannot plan" in result.output


def test_cli_rejects_invalid_rule(folders):
    source, destination = folders
    result = runner.invoke(
        app,
        [
            "organize",
            str(source),
            "-d",
            str(destination),
            "--mode",
            "category",
            "--category",
            "unsafe=pdf",
        ],
    )
    assert result.exit_code == 2
    assert "Invalid extensions" in result.output
