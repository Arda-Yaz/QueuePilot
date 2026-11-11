"""Recoverable source snapshots for training, including uncommitted source bytes."""

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import TypedDict


class SourceFile(TypedDict):
    sha256: str
    content_base64: str


class SourceSnapshot(TypedDict):
    schema_version: int
    git_commit: str | None
    git_dirty: bool | None
    source_tree_sha256: str
    files: dict[str, SourceFile]


def capture_training_source(root: Path) -> SourceSnapshot:
    """Snapshot Python sources and configuration; never include data or credentials.

    The embedded bytes make a dirty run recoverable without relying on an
    uncommitted diff surviving. The tree hash covers sorted paths and byte hashes.
    Git dirty covers the whole repository; the source hash covers the explicit
    training scope, including new/ignored Python files under src.
    """
    paths = set((root / "src").rglob("*.py"))
    paths.update((root / "requirements").glob("*.txt"))
    paths.update((root / "requirements").glob("*.in"))
    paths.update(root / p for p in ("params.yaml", "pyproject.toml", ".gitattributes"))
    files: dict[str, SourceFile] = {}
    for path in sorted(paths):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError(f"Source snapshot cannot follow links outside its root: {path}")
        content = path.read_bytes()
        files[path.relative_to(root).as_posix()] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    tree = {name: entry["sha256"] for name, entry in files.items()}
    tree_hash = hashlib.sha256(json.dumps(tree, sort_keys=True).encode("utf-8")).hexdigest()
    commit = None
    dirty = None
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=root, stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if Path(git_root).resolve() == root.resolve():
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            ).strip()
            dirty = bool(subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
            ))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # An exported source tree still has a complete recoverable snapshot.
    return {"schema_version": 1, "git_commit": commit, "git_dirty": dirty,
            "source_tree_sha256": tree_hash, "files": files}


def assert_training_source_unchanged(snapshot: SourceSnapshot, root: Path) -> None:
    current = capture_training_source(root)
    if (current["source_tree_sha256"] != snapshot["source_tree_sha256"]
            or current["git_commit"] != snapshot["git_commit"]):
        raise RuntimeError("Training source changed during the run; refusing to publish metadata")
