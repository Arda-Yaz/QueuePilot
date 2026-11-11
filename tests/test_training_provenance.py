"""Recoverable training sources and real synthetic metadata writers."""

import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from src.provenance import assert_training_source_unchanged, capture_training_source


def make_source(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "train.py").write_bytes(b"x = 1\r\n")
    (root / "requirements").mkdir()
    (root / "requirements" / "dev.txt").write_text("package==1\n")
    for name in ("params.yaml", "dvc.yaml", "pyproject.toml", ".gitattributes"):
        (root / name).write_text("config\n")


def test_source_snapshot_is_recoverable_without_git(tmp_path: Path) -> None:
    make_source(tmp_path)
    with patch("src.provenance.subprocess.check_output", side_effect=FileNotFoundError):
        snapshot = capture_training_source(tmp_path)
        assert snapshot["git_commit"] is None
        assert snapshot["git_dirty"] is None
        assert_training_source_unchanged(snapshot, tmp_path)
    record = snapshot["files"]["src/train.py"]
    assert base64.b64decode(record["content_base64"]) == b"x = 1\r\n"
    assert record["sha256"] == hashlib.sha256(b"x = 1\r\n").hexdigest()


@pytest.mark.parametrize("change", ["edit", "new", "delete", "params", "profile"])
def test_changes_during_training_are_rejected(tmp_path: Path, change: str) -> None:
    make_source(tmp_path)
    snapshot = capture_training_source(tmp_path)
    if change == "edit":
        (tmp_path / "src" / "train.py").write_text("x = 2\n")
    elif change == "new":
        (tmp_path / "src" / "new.py").write_text("x = 3\n")
    elif change == "delete":
        (tmp_path / "src" / "train.py").unlink()
    elif change == "params":
        (tmp_path / "params.yaml").write_text("new config\n")
    else:
        (tmp_path / "requirements" / "dev.txt").write_text("package==2\n")
    with pytest.raises(RuntimeError, match="source changed"):
        assert_training_source_unchanged(snapshot, tmp_path)


def test_clean_and_dirty_git_identity(tmp_path: Path) -> None:
    make_source(tmp_path)
    head = "a" * 40
    with patch("src.provenance.subprocess.check_output", side_effect=[
        str(tmp_path), head, b"", str(tmp_path), head, b" M src/train.py\n",
    ]):
        clean = capture_training_source(tmp_path)
        dirty = capture_training_source(tmp_path)
    assert clean["git_commit"] == dirty["git_commit"] == head
    assert clean["git_dirty"] is False
    assert dirty["git_dirty"] is True


@pytest.mark.parametrize("backend", ["baseline", "cnn"])
def test_training_writes_recoverable_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str,
) -> None:
    """Exercise real fitting and metadata writers on a tiny synthetic dataset."""
    from src import train_baseline, train_cnn

    make_source(tmp_path)
    source = Path(__file__).resolve().parents[1]
    params = yaml.safe_load((source / "params.yaml").read_text())
    params["baseline"].update({"min_df": 1, "max_df": 1.0, "max_features": 50})
    params["cnn"].update({"max_epochs": 1, "batch_size": 16, "embedding_dim": 4,
                          "num_filters": 2, "kernel_sizes": [2], "min_freq": 1})
    (tmp_path / "params.yaml").write_text(yaml.safe_dump(params))
    data = pd.DataFrame({"Document": ["broken laptop hardware ticket"] * 10
                         + ["account access password ticket"] * 10,
                         "Topic_group": ["Hardware"] * 10 + ["Access"] * 10})
    data_path = tmp_path / "data.csv"
    data.to_csv(data_path, index=False)
    artifacts = tmp_path / "artifacts"
    metrics = tmp_path / "metrics"
    module = train_baseline if backend == "baseline" else train_cnn
    monkeypatch.setenv("MLFLOW_TRACKING_ENABLED", "false")
    monkeypatch.setattr(module, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(module, "DATA_PATH", data_path)
    monkeypatch.setattr(module, "ARTIFACT_DIR", artifacts)
    monkeypatch.setattr(module, "load_data", lambda: data)
    monkeypatch.setattr(module, "load_splits", lambda _: SimpleNamespace(train=data, tune=data))
    if backend == "baseline":
        monkeypatch.setattr(module, "METRICS_DIR", metrics)
        train_baseline.train_baseline()
        metadata_path = artifacts / "baseline_metadata.json"
        model_path = artifacts / "baseline.joblib"
    else:
        monkeypatch.setattr(train_cnn, "CNN_DIR", artifacts / "cnn")
        train_cnn.train_cnn()
        metadata_path = artifacts / "cnn" / "cnn_metadata.json"
        model_path = artifacts / "cnn" / "textcnn.pt"
    metadata = json.loads(metadata_path.read_text())
    snapshot = metadata["source_provenance"]
    assert snapshot["source_tree_sha256"] == metadata["source_tree_sha256"]
    assert snapshot["git_commit"] == metadata["git_commit"]
    assert snapshot["git_dirty"] == metadata["git_dirty"]
    assert metadata["model_sha256"] == hashlib.sha256(model_path.read_bytes()).hexdigest()
    for entry in snapshot["files"].values():
        assert hashlib.sha256(base64.b64decode(entry["content_base64"])).hexdigest() == entry["sha256"]
