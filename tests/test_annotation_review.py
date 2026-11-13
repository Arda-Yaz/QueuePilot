"""Blind sampling, provisional annotation integrity, and anti-leakage gates."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from annotation import review_tools
from experiments.independent_data import text_hash


def prepare_fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    source = pd.DataFrame({
        "id": list("1234567"),
        "text": ["same ticket", " same  ticket ", "alpha ticket", "beta ticket", "old ticket", "conflict", "CONFLICT"],
        "category_truth": ["A", "A", "B", "B", "B", "A", "B"],
        "source_split": ["train", "test", "train", "test", "train", "train", "test"],
    })
    monkeypatch.setattr(review_tools, "load_pinned_corpus", lambda _: source.copy())
    monkeypatch.setattr(review_tools, "original_text_hashes", lambda _: {text_hash("old ticket")})
    output = root / "pilot"
    manifest = review_tools.prepare(root, output, n=2)
    return output, manifest


def test_sampling_is_grouped_blind_and_quarantines_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, manifest = prepare_fixture(tmp_path, monkeypatch)
    blind = pd.read_csv(output / "review_blind.csv")
    reserve = pd.read_csv(output / "reserved_unreviewed_pool.csv")
    assert manifest["conflicting_text_groups_quarantined"] == 1
    assert manifest["original_overlap_rows_excluded"] == 1
    assert manifest["eligible_unique_groups"] == 3
    assert not set(blind["text_sha256"]) & set(reserve["text_sha256"])
    assert "category_truth" not in blind.columns
    assert "predicted_label" not in blind.columns
    assert "model_confidence" not in blind.columns
    assert manifest["automatic_gold_export"] is False


def proposals(output: Path) -> list[dict[str, str]]:
    ids = pd.read_csv(output / "review_blind.csv")["annotation_id"]
    return [{"annotation_id": i, "proposed_label": "", "status": "INSUFFICIENT_CONTEXT",
             "confidence": "high", "rationale": "Synthetic unit fixture lacks a clear intent"} for i in ids]


def test_ai_proposals_remain_non_gold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, _ = prepare_fixture(tmp_path, monkeypatch)
    summary = review_tools.record_proposals(output, proposals(output))
    assert summary["gold_rows"] == summary["human_adjudicated_rows"] == 0
    assert summary["eligible_for_independent_audit"] is False
    with pytest.raises(FileExistsError):
        review_tools.record_proposals(output, proposals(output))


@pytest.mark.parametrize("problem", ["duplicate_id", "unknown_label", "forced_unresolved", "missing_rationale"])
def test_invalid_proposals_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str) -> None:
    output, _ = prepare_fixture(tmp_path, monkeypatch)
    items = proposals(output)
    if problem == "duplicate_id":
        items[1]["annotation_id"] = items[0]["annotation_id"]
    elif problem == "unknown_label":
        items[0].update(status="LABELABLE", proposed_label="Invented label")
    elif problem == "forced_unresolved":
        items[0]["proposed_label"] = "Hardware"
    else:
        items[0]["rationale"] = ""
    with pytest.raises(ValueError):
        review_tools.record_proposals(output, items)


def test_human_approval_cannot_turn_inspected_pilot_into_audit_data() -> None:
    with pytest.raises(ValueError, match="Development pilot"):
        review_tools.require_audit_eligibility({"status": "development_pilot_not_independent_audit",
            "taxonomy_approved": True, "annotation_origin": "human_adjudicated", "gold_rows": 64, "total_rows": 64})


def test_modified_blind_sheet_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, _ = prepare_fixture(tmp_path, monkeypatch)
    items = proposals(output)
    path = output / "review_blind.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="sheet changed"):
        review_tools.record_proposals(output, items)
