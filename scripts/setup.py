"""Idempotent local setup. Never provisions or modifies a hosted database."""

import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if sys.version_info[:2] != (3, 13):
        raise SystemExit("Use Python 3.13; see .python-version.")
    environment = ROOT / ".venv"
    if not environment.exists():
        venv.create(environment, with_pip=True)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", "requirements-dev.lock"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", "."],
        cwd=ROOT,
        check=True,
    )
    for template, destination in [
        (".env.example", ".env"),
        ("apps/web/.env.example", "apps/web/.env.local"),
    ]:
        if not (ROOT / destination).exists():
            shutil.copyfile(ROOT / template, ROOT / destination)
    print(
        "Contributor setup complete. Starting services and setting up a database are optional; "
        "see README.md."
    )


if __name__ == "__main__":
    main()
