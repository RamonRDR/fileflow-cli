"""Validate the built wheel in a disposable venv without publishing a package."""

import os
import subprocess
import sys
import venv
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    wheels = list(Path("dist").glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built wheel in dist/")
    with TemporaryDirectory(prefix="fileflow-wheel-") as temporary:
        root = Path(temporary) / "venv"
        # The CI interpreter already installed Typer/Rich/PyYAML; the wheel itself
        # is installed separately and without using a package index.
        venv.create(root, with_pip=True, system_site_packages=True)
        python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps",
             str(wheels[0].resolve())],
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-c",
                "from pathlib import Path; import sys, fileflow; "
                "assert Path(fileflow.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())",
            ],
            check=True,
        )
        for arguments in (("--help",), ("organize", "--help"), ("undo", "--help")):
            subprocess.run(
                [str(python), "-m", "fileflow", *arguments],
                check=True,
                capture_output=True,
                text=True,
            )
    print("Built wheel installed and CLI entry points verified in temporary venv.")


if __name__ == "__main__":
    main()
