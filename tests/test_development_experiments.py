"""Guard development-only data access, slice interpretation and ablation fairness."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from experiments import development_analysis as analysis
from experiments.compare_word_char import build_candidate, meets_screen
from src.train_baseline import build_baseline_pipeline


def test_loader_opens_only_train_and_checkpoint_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "data_manifest.json").write_text(json.dumps({
        "protocol_version": 2, "dataset_sha256": "raw", "train_rows": 2, "checkpoint_rows": 1,
    }))
    pd.DataFrame({"id": ["a", "b"]}).to_csv(tmp_path / "train_ids.csv", index=False)
    pd.DataFrame({"id": ["c"]}).to_csv(tmp_path / "checkpoint_ids.csv", index=False)
    monkeypatch.setattr(analysis, "REPORT_DATA_DIR", tmp_path)
    monkeypatch.setattr(analysis, "calculate_file_sha256", lambda _: "raw")
    source = pd.DataFrame({"Document": ["a", "b", "c", "forbidden holdout"],
                           "Topic_group": ["A", "B", "A", "B"]}, index=list("abcd"))
    monkeypatch.setattr(analysis, "load_data", lambda: source)
    train, checkpoint = analysis.load_development_data()
    assert train.index.tolist() == ["a", "b"]
    assert checkpoint.index.tolist() == ["c"]
    # No holdout ID file exists, so broad load_splits() could not succeed here.


def test_loader_rejects_overlap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data_manifest.json").write_text(json.dumps({
        "protocol_version": 2, "dataset_sha256": "raw", "train_rows": 1, "checkpoint_rows": 1,
    }))
    for name in ("train", "checkpoint"):
        pd.DataFrame({"id": ["a"]}).to_csv(tmp_path / f"{name}_ids.csv", index=False)
    monkeypatch.setattr(analysis, "REPORT_DATA_DIR", tmp_path)
    monkeypatch.setattr(analysis, "calculate_file_sha256", lambda _: "raw")
    with pytest.raises(RuntimeError, match="overlap"):
        analysis.load_development_data()


def test_true_class_and_predicted_queue_slices_are_distinct() -> None:
    frame = pd.DataFrame({"true_label": ["A", "A", "B", "B"],
                          "predicted_label": ["A", "B", "B", "B"],
                          "confidence": [0.9] * 4, "correct": [True, False, True, True],
                          "true_in_top3": [True] * 4})
    result = analysis.summarize(frame, ["A", "B", "C"])
    groups = result["fixed_threshold_diagnostic"]["accepted_by"]
    assert groups["true_label"][0]["accuracy"] == 0.5
    assert groups["predicted_label"][0]["accuracy"] == 1.0
    assert result["confusion_by_true_class"][2] == [0.0, 0.0, 0.0]


def test_ablation_changes_features_but_preserves_word_and_classifier_parameters() -> None:
    params = {"ngram_range": [1, 2], "min_df": 2, "max_df": 0.98,
              "max_features": 100000, "max_iter": 2000, "class_weight": "balanced"}
    original = build_baseline_pipeline(params)
    candidate = build_candidate(params)
    features = dict(candidate.named_steps["features"].transformer_list)
    assert features["word"].get_params() == original.named_steps["tfidf"].get_params()
    assert candidate.named_steps["classifier"].get_params() == original.named_steps["classifier"].get_params()
    assert features["char"].analyzer == "char_wb"


def screen_record(f1: float, coverage: float, admin: float) -> dict[str, Any]:
    return {"analysis": {"classification": {"macro avg": {"f1-score": f1},
                                              "Administrative rights": {"f1-score": admin}}},
            "coverage": {"eligible": True, "selected": {"coverage": coverage}}}


@pytest.mark.parametrize("f1,coverage,admin,expected", [
    (0.88, 0.82, 0.83, True), (0.86, 0.82, 0.83, False),
    (0.88, 0.805, 0.83, False), (0.88, 0.82, 0.79, False),
])
def test_screen_cannot_hide_metric_tradeoffs(
    f1: float, coverage: float, admin: float, expected: bool,
) -> None:
    assert meets_screen(screen_record(0.87, 0.8, 0.83),
                        screen_record(f1, coverage, admin)) is expected
