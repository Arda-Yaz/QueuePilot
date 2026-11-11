"""CNN prediction, bundle and threshold provenance regressions."""

import json
from pathlib import Path

import pytest

from src import evaluate_routing
from src.prediction_provenance import (
    cnn_bundle_hashes,
    provenance_path,
    validate_prediction_provenance,
    write_prediction_provenance,
)


def make_predictions(root: Path) -> tuple[Path, Path]:
    model = root / "textcnn.pt"
    for name in ("textcnn.pt", "vocab.json", "labels.json", "config.json"):
        (root / name).write_bytes(name.encode())
    predictions = root / "predictions.csv"
    predictions.write_text("confidence,correct\n0.9,True\n0.2,False\n", encoding="utf-8")
    write_prediction_provenance(predictions, model, cnn_bundle_hashes(model))
    return predictions, model


@pytest.mark.parametrize("problem", ["missing", "malformed", "model", "vocab", "labels", "config", "csv"])
def test_stale_prediction_bundle_is_rejected(tmp_path: Path, problem: str) -> None:
    predictions, model = make_predictions(tmp_path)
    if problem == "missing":
        provenance_path(predictions).unlink()
    elif problem == "malformed":
        provenance_path(predictions).write_text("[]")
    else:
        path = {"model": model, "csv": predictions}.get(problem, tmp_path / f"{problem}.json")
        path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(RuntimeError, match="prediction provenance"):
        validate_prediction_provenance(predictions, model)


def test_publisher_rejects_model_change_during_predictions(tmp_path: Path) -> None:
    predictions, model = make_predictions(tmp_path)
    initial = cnn_bundle_hashes(model)
    model.write_bytes(b"new model")
    with pytest.raises(RuntimeError, match="bundle changed"):
        write_prediction_provenance(predictions, model, initial)


@pytest.mark.parametrize("threshold_hash", [None, "stale", "matching"])
def test_routing_requires_predictions_and_threshold_from_same_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, threshold_hash: str | None,
) -> None:
    predictions, model = make_predictions(tmp_path)
    sha = validate_prediction_provenance(predictions, model)
    threshold = tmp_path / "threshold.json"
    threshold.write_text(json.dumps({"threshold": 0.5,
                                     "model_sha256": sha if threshold_hash == "matching" else threshold_hash}))
    output = tmp_path / "routing.json"
    for name, path in {"TEST_PREDICTIONS_PATH": predictions, "CNN_MODEL_PATH": model,
                       "THRESHOLD_PATH": threshold, "OUTPUT_PATH": output}.items():
        monkeypatch.setattr(evaluate_routing, name, path)
    if threshold_hash != "matching":
        with pytest.raises(RuntimeError, match="Threshold/model mismatch"):
            evaluate_routing.main()
        assert not output.exists()
    else:
        evaluate_routing.main()
        report = json.loads(output.read_text())
        assert report["model_sha256"] == sha
        assert report["coverage"] == 0.5
        assert report["auto_routed_accuracy"] == 1.0
