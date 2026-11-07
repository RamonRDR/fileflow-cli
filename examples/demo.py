"""End-to-end demonstration entirely inside a temporary directory."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run(*arguments: object) -> None:
    args = [sys.executable, "-m", "fileflow", *(str(value) for value in arguments)]
    print("$ python -m fileflow " + " ".join(str(value) for value in arguments), flush=True)
    env = {**os.environ, "NO_COLOR": "1"}
    result = subprocess.run(args, capture_output=True, text=True, env=env, check=False)
    print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, file=sys.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f"CLI exited with {result.returncode}: {arguments}")


def main() -> None:
    with TemporaryDirectory(prefix="fileflow-demo-") as temporary:
        sandbox = Path(temporary)
        source = sandbox / "inbox"
        destination = sandbox / "sorted"
        (source / "nested").mkdir(parents=True)
        (destination / "Research").mkdir(parents=True)
        (source / "nested" / "report.pdf").write_text("new research", encoding="utf-8")
        (source / "photo.PNG").write_bytes(b"example image bytes")
        (source / "temporary.tmp").write_text("keep at source", encoding="utf-8")
        prior = destination / "Research" / "report.pdf"
        prior.write_text("existing document", encoding="utf-8")
        config = sandbox / "rules.yaml"
        config.write_text(
            "version: 1\nmode: category\nrecursive: true\n"
            "categories:\n  Research: [.pdf]\nexclude: ['*.tmp']\n",
            encoding="utf-8",
        )

        print("=== PREVIEW ===", flush=True)
        run("organize", source, "-d", destination, "--config", config, "--dry-run")
        assert (source / "nested" / "report.pdf").exists()
        assert not (destination / "Research" / "report (1).pdf").exists()

        print("=== EXECUTE ===", flush=True)
        run("organize", source, "-d", destination, "--config", config)
        assert prior.read_text(encoding="utf-8") == "existing document"
        assert (destination / "Research" / "report (1).pdf").read_text(
            encoding="utf-8"
        ) == "new research"
        assert (source / "temporary.tmp").exists()
        manifests = list((destination / ".fileflow" / "manifests").glob("*.json"))
        assert len(manifests) == 1

        print("=== UNDO PREVIEW ===", flush=True)
        run("undo", manifests[0], "--dry-run")
        assert not (source / "nested" / "report.pdf").exists()

        print("=== UNDO ===", flush=True)
        run("undo", manifests[0])
        assert (source / "nested" / "report.pdf").read_text(encoding="utf-8") == "new research"
        assert (source / "photo.PNG").exists()
        assert (source / "temporary.tmp").exists()
        assert prior.read_text(encoding="utf-8") == "existing document"
        assert not (destination / "Research" / "report (1).pdf").exists()
        print("Demo completed safely; temporary files will now be discarded.", flush=True)


if __name__ == "__main__":
    main()
