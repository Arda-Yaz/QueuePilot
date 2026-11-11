"""Historical LF migration integrity and newline regression checks."""

import hashlib
import json
from pathlib import Path

import yaml


def test_lock_migration_preserves_original_run_outputs() -> None:
    history = Path(__file__).resolve().parents[1] / "docs/history/2026-11-11-lock"
    migration = json.loads((history / "migration.json").read_text())
    old_bytes = (history / "original.dvc.lock").read_bytes()
    new_bytes = (history / "lf.dvc.lock").read_bytes()
    assert hashlib.sha256(old_bytes).hexdigest() == migration["original_lock_sha256"]
    assert hashlib.sha256(new_bytes).hexdigest() == migration["lf_lock_sha256"]
    expected = yaml.safe_load(old_bytes)
    changed = 0
    for stage in expected["stages"].values():
        for dep in stage.get("deps", []):
            change = migration["sources"].get(dep["path"])
            if change:
                assert dep["md5"] == change["old_md5"]
                dep["md5"], dep["size"] = change["lf_md5"], change["lf_size"]
                changed += 1
    assert changed == migration["changed_records"] == 11
    assert yaml.safe_load(new_bytes) == expected


def test_no_newline_only_dvc_source_mismatch() -> None:
    """Catch the LF Git / CRLF lock bug without blessing functional source edits.

    This focused CI gate needs neither private raw data nor ignored prediction
    CSVs. It does not replace a full fresh-checkout DVC status assertion.
    """
    root = Path(__file__).resolve().parents[1]
    lock = yaml.safe_load((root / "dvc.lock").read_bytes())
    for stage in lock["stages"].values():
        for dep in stage.get("deps", []):
            if not dep["path"].startswith("src/") or not dep["path"].endswith(".py"):
                continue
            content = (root / dep["path"]).read_bytes().replace(b"\r\n", b"\n")
            if hashlib.md5(content).hexdigest() != dep["md5"]:
                assert hashlib.md5(content.replace(b"\n", b"\r\n")).hexdigest() != dep["md5"], dep["path"]
