"""Versioned YAML parsing tests, isolated from personal directories."""

import pytest
from typer.testing import CliRunner

from fileflow.cli import app
from fileflow.config import load_config
from fileflow.models import SortMode

runner = CliRunner()


def test_valid_yaml_settings(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "version: 1\nmode: category\nrecursive: true\nby_date: true\n"
        "categories:\n  Research: [.pdf, .ipynb]\nexclude: ['*.tmp', 'cache/**']\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.mode is SortMode.category
    assert config.by_date and config.recursive
    assert config.category_rules == ("Research=.pdf,.ipynb",)
    assert config.exclude == ("*.tmp", "cache/**")


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "mode: category",
        "version: true",
        "version: 2",
        "version: 1\nunknown: true",
        "version: 1\nmode: other",
        "version: 1\nrecursive: 'true'",
        "version: 1\ncategories: []",
        "version: 1\ncategories:\n  Bad: .pdf",
        "version: 1\ncategories:\n  ../escape: [.pdf]",
        "version: 1\nexclude: bad",
        "version: 1\nexclude: ['../escape']",
        "version: 1\nexclude: ['']",
        "version: 1\nexclude: [123]",
        "version: 1\nx: !!python/object/apply:os.system ['echo wrong']",
        "version: 1\ncategories: {A: [}",
    ],
)
def test_invalid_yaml_rejected(tmp_path, content):
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_yaml_cli_dry_run_applies_all_filters(folders, tmp_path):
    source, destination = folders
    (source / "nested").mkdir()
    (source / "nested" / "keep.pdf").write_text("keep", encoding="utf-8")
    (source / "nested" / "skip.tmp").write_text("skip", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        "version: 1\nmode: category\nrecursive: true\n"
        "categories:\n  Papers: [.pdf]\nexclude: ['*.tmp']\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["organize", str(source), "-d", str(destination), "--config", str(config), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "1 planned" in result.output
    assert "1 ignored" in result.output
    assert not destination.exists()


def test_invalid_yaml_cli_returns_exit_two(folders, tmp_path):
    source, destination = folders
    config = tmp_path / "wrong.yaml"
    config.write_text("version: 1\nrecursive: bad\n", encoding="utf-8")
    result = runner.invoke(
        app, ["organize", str(source), "-d", str(destination), "--config", str(config)]
    )
    assert result.exit_code == 2
    assert not destination.exists()
