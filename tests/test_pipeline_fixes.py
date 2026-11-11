"""Integrity regressions for persisted splits, reports and model selection."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from app import main as api
from src.data import validate_persisted_splits
from src.inference import get_predictor
from src.select_model import CandidateResult, select_candidate


@pytest.mark.parametrize("total", [4, 5, None])
def test_missing_row_cannot_be_hidden_by_manifest(total: int | None) -> None:
    df = pd.DataFrame(index=list("abcde"))
    manifest: dict[str, object] = {"dataset_sha256": "sha", "total_rows": total}
    with patch("src.data.calculate_file_sha256", return_value="sha"):
        with pytest.raises(RuntimeError, match="do not cover"):
            validate_persisted_splits(df, pd.Index(["a"]), pd.Index(["b"]),
                                      pd.Index(["c"]), manifest, pd.Index(["d"]))


def test_duplicate_within_partition_is_rejected() -> None:
    with patch("src.data.calculate_file_sha256", return_value="sha"):
        with pytest.raises(RuntimeError, match="duplicate"):
            validate_persisted_splits(pd.DataFrame(index=list("abcd")),
                                      pd.Index(["a", "a"]), pd.Index(["b"]),
                                      pd.Index(["c"]), {"dataset_sha256": "sha", "total_rows": 4},
                                      pd.Index(["d"]))


@pytest.mark.parametrize("backend", ["baseline", "cnn"])
@pytest.mark.parametrize("problem", ["none", "missing", "malformed", "stale"])
def test_model_info_uses_loaded_backend_and_matching_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str, problem: str,
) -> None:
    monkeypatch.setattr(api, "METRICS_DIR", tmp_path)
    monkeypatch.setattr(api.app.state, "predictor",
                        SimpleNamespace(backend=backend, model_sha256="active"), raising=False)
    names = ["baseline_routing_metrics.json" if backend == "baseline" else "routing_metrics.json",
             f"{backend}_metrics.json", f"{backend}_calibration_holdout_metrics.json"]
    for filename in names:
        (tmp_path / filename).write_text(json.dumps({"model_sha256": "active", "backend": backend}),
                                        encoding="utf-8")
    path = tmp_path / names[-1]
    if problem == "missing":
        path.unlink()
    elif problem == "malformed":
        path.write_text("{", encoding="utf-8")
    elif problem == "stale":
        path.write_text('{"model_sha256": "old"}', encoding="utf-8")
    result = api.model_info()
    assert result["available"] is (problem == "none")
    assert result["model_backend"] == backend
    if problem == "none":
        assert result["routing"] == {"model_sha256": "active", "backend": backend}


def test_auto_backend_rejects_stale_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"selected_backend": "baseline",
                                    "selected_model_sha256": "old", "selected_threshold": 0.5}),
                         encoding="utf-8")
    monkeypatch.setattr("src.inference.MODEL_SELECTION_PATH", selection)
    monkeypatch.setattr("src.inference.BaselinePredictor",
                        lambda: SimpleNamespace(model_sha256="new", threshold=0.5))
    with pytest.raises(RuntimeError, match="selection is stale"):
        get_predictor("auto")


@pytest.mark.parametrize("coverage,winner", [(0.81, "baseline"), (0.83, "cnn")])
def test_cnn_promotion_requires_configured_margin(coverage: float, winner: str) -> None:
    baseline: CandidateResult = {
        "backend": "baseline", "validation_accuracy": 0.95,
        "validation_macro_f1": 0.9, "threshold": 0.6, "validation_coverage": 0.8,
        "validation_auto_routed_accuracy": 0.95, "validation_accuracy_ci_lower": 0.91,
        "model_sha256": "baseline-sha",
    }
    cnn: CandidateResult = {**baseline, "backend": "cnn", "validation_coverage": coverage}
    assert select_candidate([baseline, cnn], 0.9, 0.02)["backend"] == winner


def test_calibration_loading_uses_full_split_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.data import load_calibration_split

    def reject(_: pd.DataFrame) -> None:
        raise RuntimeError("invalid full split")

    monkeypatch.setattr("src.data.load_splits", reject)
    with pytest.raises(RuntimeError, match="invalid full split"):
        load_calibration_split(pd.DataFrame())
