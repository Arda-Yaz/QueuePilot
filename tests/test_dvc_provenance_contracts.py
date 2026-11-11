"""DVC dependency contracts for training and prediction provenance."""

from pathlib import Path

import yaml

from src.provenance import capture_training_source


def test_dvc_tracks_source_snapshot_and_cnn_prediction_inputs() -> None:
    root = Path(__file__).resolve().parents[1]
    stages = yaml.safe_load((root / "dvc.yaml").read_text())["stages"]
    snapshot = capture_training_source(root)
    for name in ("train_baseline", "train_cnn"):
        assert set(snapshot["files"]) <= set(stages[name]["deps"])
    routing_deps = set(stages["evaluate_routing_cnn"]["deps"])
    assert {"artifacts/cnn/textcnn.pt", "artifacts/cnn/vocab.json", "artifacts/cnn/config.json",
            "artifacts/cnn/labels.json", "reports/metrics/cnn_test_predictions.provenance.json",
            "src/prediction_provenance.py"} <= routing_deps
    assert {"reports/metrics/cnn_test_predictions.provenance.json": {"cache": False}} in stages["evaluate_cnn"]["outs"]
