"""Validate README pytest badge counts against actual CI JUnit results."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READMES = ("README.md", "README.pt-BR.md", "README.es.md")
BADGE_RE = re.compile(
    r"!\[pytest\]\(https://img\.shields\.io/badge/pytest-(\d+)%20passing-[A-Za-z0-9]+\)"
)
IMAGE_RE = re.compile(r"!\[[^\]]+\]\((https://(?:img\.shields\.io|github\.com)/[^\s)]+)\)")


def passed_from_junit(report: Path) -> tuple[int, int, int, int, int]:
    root = ET.parse(report).getroot()
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.findall("testsuite"))
    else:
        raise ValueError(f"Unexpected JUnit root tag: {root.tag}")
    if not suites:
        raise ValueError("JUnit report has no testsuites")
    total = sum(int(s.get("tests", "0")) for s in suites)
    failed = sum(int(s.get("failures", "0")) for s in suites)
    errors = sum(int(s.get("errors", "0")) for s in suites)
    skipped = sum(int(s.get("skipped", "0")) for s in suites)
    passed = total - failed - errors - skipped
    if total <= 0 or passed < 0:
        raise ValueError("JUnit report has invalid test totals")
    return passed, total, failed, errors, skipped


def check_readmes(passed: int) -> None:
    headers = []
    for name in READMES:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        matches = BADGE_RE.findall(text)
        if len(matches) != 1:
            raise ValueError(f"{name}: expected exactly one pytest passing-count badge")
        shown = int(matches[0])
        if shown != passed:
            raise ValueError(
                f"{name}: pytest badge says {shown} passing; CI measured {passed}. "
                "Update all three README badges in the same PR."
            )
        start = text.find('<div align="center">')
        end = text.find("</div>", start)
        if start < 0 or end < 0:
            raise ValueError(f"{name}: missing centered header")
        badges = IMAGE_RE.findall(text[start:end])
        if len(badges) != 14:
            raise ValueError(f"{name}: expected 14 technical badges, found {len(badges)}")
        headers.append(badges)
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if re.match(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|#)", link):
                continue
            local = link.split("#", 1)[0]
            if local and not (ROOT / local).is_file():
                raise ValueError(f"{name}: missing relative link target: {link}")
    if headers[0] != headers[1] or headers[0] != headers[2]:
        raise ValueError("Technical badge URLs differ across README languages")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/verify_readme_badges.py <pytest-junit.xml>", file=sys.stderr)
        return 2
    try:
        passed, total, failed, errors, skipped = passed_from_junit(Path(sys.argv[1]))
        check_readmes(passed)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"README badge validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"README badges verified in EN/PT-BR/ES: {passed} passing "
        f"({total} collected, {failed} failed, {errors} errors, {skipped} skipped)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
