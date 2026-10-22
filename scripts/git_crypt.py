"""Initialize git-crypt and stage explicitly selected environment files safely."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAGIC = b"\x00GITCRYPT\x00"


def run(arguments: list[str], root: Path) -> bytes:
    result = subprocess.run(arguments, cwd=root, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(message or f"{arguments[0]} failed.")
    return result.stdout


def secret_environment(path: Path) -> bool:
    return (path.name == ".env" or path.name.startswith(".env.")) and not path.name.endswith(
        ".example"
    )


def require_initialized(root: Path) -> None:
    location = run(["git", "rev-parse", "--git-path", "git-crypt/keys/default"], root)
    key = root / location.decode().strip()
    if not key.is_file():
        raise RuntimeError(
            "git-crypt is not unlocked. Initialize a new repo or unlock an existing one."
        )
    required = run(["git", "config", "--local", "--get", "filter.git-crypt.required"], root)
    if required.strip() != b"true":
        raise RuntimeError(
            "The required git-crypt filter is not configured; refusing to stage secrets."
        )


def initialize(root: Path = ROOT) -> None:
    if shutil.which("git-crypt") is None:
        raise RuntimeError("Install git-crypt first; see docs/SECRETS.md.")
    if not (root / ".git").exists():
        run(["git", "init", "-b", "main"], root)
    top_level = Path(run(["git", "rev-parse", "--show-toplevel"], root).decode().strip())
    if top_level.resolve() != root.resolve():
        raise RuntimeError("Run initialization at Vantage's own repository root.")
    location = run(["git", "rev-parse", "--git-path", "git-crypt/keys/default"], root)
    if (root / location.decode().strip()).is_file():
        require_initialized(root)
        return
    tracked = run(["git", "ls-files", "-z"], root).decode().split("\0")
    if any(path.startswith(".git-crypt/") for path in tracked):
        raise RuntimeError("This repository has an existing encryption key; use git-crypt unlock.")
    for name in filter(None, tracked):
        if secret_environment(Path(name)):
            raise RuntimeError(
                "Environment files are already tracked. Review their history before initializing "
                "or unlock the repository's existing key."
            )
    run(["git-crypt", "init"], root)
    require_initialized(root)


def track(paths: list[str], root: Path = ROOT) -> None:
    require_initialized(root)
    selected = []
    for value in paths:
        path = (root / value).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise RuntimeError("Select an existing environment file inside this repository.")
        if not secret_environment(path):
            raise RuntimeError("Only non-template .env or .env.* files may be explicitly tracked.")
        relative = path.relative_to(root.resolve()).as_posix()
        attributes = run(["git", "check-attr", "-z", "filter", "--", relative], root).split(b"\0")
        if len(attributes) < 3 or attributes[2] != b"git-crypt":
            raise RuntimeError("The selected file does not have a git-crypt encryption rule.")
        selected.append(relative)
    for relative in selected:
        run(["git", "add", "--force", "--", relative], root)
        staged = run(["git", "show", f":{relative}"], root)
        if not staged.startswith(MAGIC):
            run(["git", "update-index", "--force-remove", "--", relative], root)
            raise RuntimeError("Encryption verification failed; the plaintext file was unstaged.")


def export_key(destination: Path, root: Path = ROOT) -> None:
    require_initialized(root)
    path = destination.expanduser().resolve()
    if path.is_relative_to(root.resolve()):
        raise RuntimeError("Export encryption keys outside the repository.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        run(["git-crypt", "export-key", str(path)], root)
        path.chmod(0o600)
    except (RuntimeError, OSError):
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Vantage environment-file encryption")
    parser.add_argument("command", choices=["init", "track", "status", "export"])
    parser.add_argument("paths", nargs="*")
    arguments = parser.parse_args()
    try:
        if arguments.command == "init":
            initialize()
            print(
                "git-crypt initialized. Environment files remain ignored until explicitly tracked."
            )
        elif arguments.command == "track":
            if not arguments.paths:
                parser.error("track requires one or more environment-file paths")
            track(arguments.paths)
            print("Selected environment files staged; encrypted index blobs verified.")
        elif arguments.command == "export":
            if len(arguments.paths) != 1:
                parser.error("export requires one destination outside the repository")
            export_key(Path(arguments.paths[0]))
            print("Encryption key exported with owner-only permissions.")
        else:
            require_initialized(ROOT)
            print(run(["git-crypt", "status"], ROOT).decode(), end="")
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
