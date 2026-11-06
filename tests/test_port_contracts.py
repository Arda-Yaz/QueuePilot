"""Regression checks for boundaries affected by the QueuePilot reorganization."""

import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.hashing import calculate_file_sha256
from src.inference import format_prediction


def test_equal_confidence_uses_source_order_and_accepts_threshold() -> None:
    probabilities = np.array([0.4, 0.4, 0.1, 0.1])
    labels = ["A", "B", "C", "D"]
    source_order = np.argsort(probabilities)[::-1]
    result = format_prediction(labels, probabilities, threshold=0.4)
    assert result["category"] == labels[int(source_order[0])]
    assert [item["category"] for item in result["top_3"]] == [
        labels[int(index)] for index in source_order[:3]
    ]
    assert result["needs_manual_review"] is False


@pytest.mark.parametrize("backend", ["baseline", "cnn"])
@pytest.mark.parametrize("correct", [True, False])
def test_threshold_cli_preserves_artifact_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str, correct: bool,
) -> None:
    module = importlib.import_module(f"src.analyze_threshold_{backend}")
    predictions = tmp_path / "predictions.csv"
    analysis = tmp_path / "analysis.csv"
    threshold = tmp_path / "threshold.json"
    model = tmp_path / "model.bin"
    model.write_bytes(b"existing fitted artifact")
    threshold.write_text('{"threshold": 0.99}', encoding="utf-8")
    (tmp_path / "params.yaml").write_text("routing: {}\n", encoding="utf-8")
    pd.DataFrame({
        "confidence": [0.8] * 200,
        "correct": [correct] * 200,
        "true_label": ["Access"] * 200,
    }).to_csv(predictions, index=False)
    for name, value in {
        "INPUT_PATH": predictions, "OUTPUT_PATH": analysis,
        "THRESHOLD_PATH": threshold, "MODEL_PATH": model, "ROOT_DIR": tmp_path,
    }.items():
        monkeypatch.setattr(module, name, value)

    if correct:
        module.main()
        config = json.loads(threshold.read_text(encoding="utf-8"))
        assert config["model_sha256"] == calculate_file_sha256(model)
        assert config["threshold"] == 0.1
        assert config["n_candidates"] == 90
    else:
        with pytest.raises(RuntimeError, match="previous threshold was removed"):
            module.main()
        assert not threshold.exists()
    assert analysis.exists()
