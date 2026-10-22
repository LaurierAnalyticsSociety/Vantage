import shutil
from pathlib import Path

import pytest

from scripts.git_crypt import MAGIC, ROOT, export_key, initialize, run, track

pytestmark = pytest.mark.skipif(
    shutil.which("git-crypt") is None, reason="git-crypt is not installed"
)


def test_encrypted_index_and_key_roundtrip_preserve_readable_templates(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    for name in [".gitattributes", ".gitignore"]:
        shutil.copyfile(ROOT / name, root / name)
    plaintext = b"SYNTHETIC_SECRET=only-a-test\n"
    (root / ".env").write_bytes(plaintext)
    (root / ".env.example").write_text("SYNTHETIC_SECRET=\n")
    initialize(root)
    initialize(root)
    track([".env"], root)
    assert run(["git", "show", ":.env"], root).startswith(MAGIC)
    assert (root / ".env").read_bytes() == plaintext
    with pytest.raises(RuntimeError, match="non-template"):
        track([".env.example"], root)
    with pytest.raises(RuntimeError, match="outside"):
        export_key(root / "accidental.key", root)
    run(["git", "add", ".env.example", ".gitattributes", ".gitignore"], root)
    assert not run(["git", "show", ":.env.example"], root).startswith(MAGIC)
    backup = tmp_path / "backup.git-crypt-key"
    export_key(backup, root)
    assert backup.stat().st_mode & 0o777 == 0o600
    run(
        [
            "git",
            "-c",
            "user.name=Vantage Test",
            "-c",
            "user.email=vantage-test@example.org",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-m",
            "Synthetic encryption test",
        ],
        root,
    )
    run(["git-crypt", "lock"], root)
    assert (root / ".env").read_bytes().startswith(MAGIC)
    run(["git-crypt", "unlock", str(backup)], root)
    assert (root / ".env").read_bytes() == plaintext
    run(["git", "config", "--local", "filter.git-crypt.required", "false"], root)
    with pytest.raises(RuntimeError, match="required git-crypt filter"):
        track([".env"], root)
