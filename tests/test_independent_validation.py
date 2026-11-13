"""Independent-data gates; all positive fixtures are synthetic, not validation evidence."""

import copy
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import pytest
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from experiments import independent_validation as validation
from experiments.independent_data import text_hash, validate_attestation, validate_frame
from src.hashing import calculate_file_sha256


def declaration() -> dict[str, Any]:
    return {"not_previously_used": True, "labels_blind_to_model_predictions": True,
            "source": "SYNTHETIC TEST ONLY", "sampling_method": "unit fixture",
            "labeling_process": "deterministic synthetic classes", "collection_window": "test run"}


def batch(prefix: str, n: int = 400) -> pd.DataFrame:
    return pd.DataFrame({"external_id": [f"{prefix}-{i}" for i in range(n)],
                         "Document": [f"{'red' if i % 2 else 'blue'} {prefix} {i}" for i in range(n)],
                         "Topic_group": ["Administrative rights" if i % 2 else "Hardware" for i in range(n)]})


@pytest.mark.parametrize("problem", ["old_text", "within_duplicate", "conflicting_duplicate", "unknown_label",
                                     "empty", "duplicate_id", "blank", "old_id"])
def test_intake_rejects_invalid_or_reused_data(problem: str) -> None:
    frame = batch("new", 4)
    forbidden: set[str] = set()
    ids: set[str] = set()
    if problem == "old_text":
        forbidden.add(text_hash("  BLUE   NEW 0 "))
    elif problem in {"within_duplicate", "conflicting_duplicate"}:
        frame.loc[1, "Document"] = frame.loc[0, "Document"]
        if problem == "within_duplicate":
            frame.loc[1, "Topic_group"] = frame.loc[0, "Topic_group"]
    elif problem == "unknown_label":
        frame.loc[0, "Topic_group"] = "Invented queue"
    elif problem == "empty":
        frame = frame.iloc[:0]
    elif problem == "duplicate_id":
        frame.loc[1, "external_id"] = frame.loc[0, "external_id"]
    elif problem == "blank":
        frame.loc[0, "Document"] = "   "
    else:
        import hashlib
        ids.add(hashlib.sha256(frame.loc[0, "external_id"].encode()).hexdigest())
    with pytest.raises(ValueError):
        validate_frame(frame, ["Administrative rights", "Hardware"], forbidden, ids)


@pytest.mark.parametrize("key", ["not_previously_used", "labels_blind_to_model_predictions", "source"])
def test_independence_declaration_is_required(key: str) -> None:
    record = declaration()
    record.pop(key)
    with pytest.raises(ValueError):
        validate_attestation(record)


def make_bundle(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = root / "old.csv"
    pd.DataFrame({"Document": ["legacy data"]}).to_csv(raw, index=False)
    monkeypatch.setattr(validation, "DATA_PATH", raw)
    bundle = root / "bundle"
    bundle.mkdir()
    model = make_pipeline(CountVectorizer(), LogisticRegression())
    model.fit(["red"] * 100 + ["blue"] * 100, ["Administrative rights"] * 100 + ["Hardware"] * 100)
    for name in ("reference", "candidate"):
        joblib.dump(model, bundle / f"{name}.joblib")
    for name in ("comparison_plan.json", "comparison_results.json"):
        validation.write_json(bundle / name, {"synthetic": True})
    validation.write_json(bundle / "source_snapshot.json", validation.source_snapshot())
    manifest = {"schema_version": 1, "policy": copy.deepcopy(validation.POLICY),
                "models": {"reference": "reference.joblib", "candidate": "candidate.joblib"},
                "labels": model.classes_.tolist(), "environment": validation.runtime_environment(),
                "original_dataset_sha256": calculate_file_sha256(raw),
                "files": {p.name: calculate_file_sha256(p) for p in bundle.iterdir()}}
    validation.write_json(bundle / "manifest.json", manifest)
    return bundle


def write_input(root: Path, prefix: str, frame: pd.DataFrame | None = None) -> tuple[Path, Path]:
    csv = root / f"{prefix}.csv"
    (batch(prefix) if frame is None else frame).to_csv(csv, index=False)
    attestation = root / f"{prefix}.json"
    validation.write_json(attestation, declaration())
    return csv, attestation


def test_synthetic_end_to_end_preserves_thresholds_and_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    csv, provenance = write_input(tmp_path, "risk")
    risk = validation.evaluate("risk", bundle, csv, provenance, tmp_path / "risk-output")
    assert risk["decision"] == "ready_for_separate_audit"
    assert risk["automatic_promotion"] is False
    csv, provenance = write_input(tmp_path, "audit")
    audit = validation.evaluate("audit", bundle, csv, provenance, tmp_path / "audit-output",
                                tmp_path / "risk-output/risk_result.json")
    assert audit["both_accuracy_gates_met"] is True
    assert audit["automatic_promotion"] is False
    assert audit["prespecified_review_screen_met"] is False  # identical pair has no coverage gain
    for name in ("reference", "candidate"):
        assert audit["models"][name]["threshold"] == risk["models"][name]["selected"]["threshold"]


def test_audit_cannot_reuse_risk_text_or_change_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    csv, provenance = write_input(tmp_path, "risk")
    validation.evaluate("risk", bundle, csv, provenance, tmp_path / "risk-output")
    reused = batch("risk")
    reused["external_id"] = [f"different-{i}" for i in range(len(reused))]
    reused["Topic_group"] = reused["Topic_group"].iloc[::-1].to_numpy()
    csv, provenance = write_input(tmp_path, "audit", reused)
    with pytest.raises(ValueError, match="overlaps"):
        validation.evaluate("audit", bundle, csv, provenance, tmp_path / "audit-output",
                            tmp_path / "risk-output/risk_result.json")


@pytest.mark.parametrize("target", ["candidate.joblib", "source_snapshot.json"])
def test_modified_frozen_bundle_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    path = bundle / target
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(RuntimeError, match="changed"):
        validation.verify_bundle(bundle)


def test_modified_risk_result_cannot_supply_new_audit_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    csv, provenance = write_input(tmp_path, "risk")
    validation.evaluate("risk", bundle, csv, provenance, tmp_path / "risk-output")
    risk_path = tmp_path / "risk-output/risk_result.json"
    result = json.loads(risk_path.read_text())
    result["models"]["candidate"]["selected"]["threshold"] = 0.99
    validation.write_json(risk_path, result)
    csv, provenance = write_input(tmp_path, "audit")
    with pytest.raises(RuntimeError, match="Risk result changed"):
        validation.evaluate("audit", bundle, csv, provenance, tmp_path / "audit-output", risk_path)


def test_failing_risk_gate_has_no_substitute_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    wrong = batch("risk")
    wrong["Topic_group"] = wrong["Topic_group"].iloc[::-1].to_numpy()
    csv, provenance = write_input(tmp_path, "risk", wrong)
    result = validation.evaluate("risk", bundle, csv, provenance, tmp_path / "risk-output")
    assert result["decision"] == "risk_gate_not_met"
    assert all(record["selected"] is None for record in result["models"].values())


def test_modified_risk_predictions_are_rejected_before_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    csv, provenance = write_input(tmp_path, "risk")
    validation.evaluate("risk", bundle, csv, provenance, tmp_path / "risk-output")
    path = tmp_path / "risk-output/candidate_predictions.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    csv, provenance = write_input(tmp_path, "audit")
    with pytest.raises(RuntimeError, match="Risk predictions changed"):
        validation.evaluate("audit", bundle, csv, provenance, tmp_path / "audit-output",
                            tmp_path / "risk-output/risk_result.json")


def test_changed_evaluator_sources_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = make_bundle(tmp_path, monkeypatch)
    monkeypatch.setattr(validation, "source_snapshot", lambda: {"changed": "source"})
    with pytest.raises(RuntimeError, match="Evaluator sources changed"):
        validation.verify_bundle(bundle)
