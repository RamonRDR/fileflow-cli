"""Category parsing, extension detection, and input hardening."""

import pytest

from fileflow.models import SortMode
from fileflow.rules import destination_group, parse_categories


def test_default_category_for_pdf(tmp_path):
    assert (
        destination_group(tmp_path / "report.PDF", SortMode.category, parse_categories(()))
        == "Documents"
    )


def test_compound_archive_extension(tmp_path):
    categories = parse_categories(())
    path = tmp_path / "bundle.tar.gz"
    assert destination_group(path, SortMode.extension, categories) == "tar.gz"
    assert destination_group(path, SortMode.category, categories) == "Archives"


def test_custom_categories_override_default(tmp_path):
    categories = parse_categories(("Research=.pdf,.ipynb",))
    assert destination_group(tmp_path / "paper.pdf", SortMode.category, categories) == "Research"
    assert destination_group(tmp_path / "notes.ipynb", SortMode.category, categories) == "Research"
    assert destination_group(tmp_path / "notes.docx", SortMode.category, categories) == "Documents"


@pytest.mark.parametrize(
    "rule",
    [
        "NoEquals",
        "../escape=.txt",
        "A/B=.txt",
        "CON=.pdf",
        "Bad.=.txt",
        "Empty=",
        "Bad=txt",
        "Bad=.txt,../../hack",
    ],
)
def test_invalid_custom_rules_rejected(rule):
    with pytest.raises(ValueError):
        parse_categories((rule,))


def test_duplicate_custom_extension_rejected():
    with pytest.raises(ValueError, match="multiple custom rules"):
        parse_categories(("Research=.pdf", "Work=.PDF"))
