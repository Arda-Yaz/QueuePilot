"""External data is hash/ID checked; fictional stress labels cannot become audit labels silently."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from benchmarks import public_data, synthetic_stress
from benchmarks.stress_scenarios import SCENARIOS
from experiments.independent_data import text_hash, validate_frame


def source_fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checksums = {}
    for split, offset in (("train", 0), ("test", 2)):
        pd.DataFrame({"id": [str(offset), str(offset + 1)], "text": ["first ticket", "second ticket"]}).to_csv(root / f"X_{split}.csv", index=False)
        # The label rows deliberately arrive in the opposite order.
        pd.DataFrame({"id": [str(offset + 1), str(offset)], "category_truth": ["second", "first"]}).to_csv(root / f"y_{split}.csv", index=False)
        for prefix in ("X", "y"):
            name = f"{prefix}_{split}.csv"
            checksums[name] = hashlib.md5((root / name).read_bytes()).hexdigest()
    monkeypatch.setattr(public_data, "CHECKSUMS", checksums)
    metadata = {"id": public_data.RECORD, "metadata": {"license": {"id": "cc-by-4.0"}},
                "files": [{"key": key, "checksum": f"md5:{sha}"} for key, sha in checksums.items()]}
    (root / "metadata.json").write_text(json.dumps(metadata))


def test_external_labels_are_joined_by_id_not_row_position(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_fixture(tmp_path, monkeypatch)
    frame = public_data.load_pinned_corpus(tmp_path)
    assert frame.loc[frame["id"] == "0", "category_truth"].item() == "first"
    assert frame.loc[frame["id"] == "1", "category_truth"].item() == "second"


def test_corrupted_public_download_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_fixture(tmp_path, monkeypatch)
    path = tmp_path / "X_train.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="checksum"):
        public_data.load_pinned_corpus(tmp_path)


def test_taxonomy_and_source_split_leakage_are_not_hidden() -> None:
    frame = pd.DataFrame({"id": ["1", "2", "3"], "text": ["Same text", " same   text ", "other"],
                          "category_truth": ["Fileservice", "O365", "Fileservice"],
                          "source_split": ["train", "test", "test"]})
    result = public_data.qualification(frame, {text_hash("other")}, ["Storage", "Access"])
    assert result["compatible_with_full_eight_class_audit"] is False
    assert result["label_mapping_applied"] is False
    assert result["exact_normalized_overlap_with_original"] == 1
    assert result["normalized_text_duplicates"] == 1
    assert result["conflicting_label_text_groups"] == 1
    assert result["source_train_test_shared_normalized_texts"] == 1


def test_stress_set_has_eighty_scenarios_and_correlated_variants() -> None:
    frame = synthetic_stress.make_cases()
    assert len(frame) == 240
    assert frame["scenario_id"].nunique() == 80
    assert set(frame["expected_label"]) == set(SCENARIOS)
    assert frame.groupby("scenario_id")["expected_label"].nunique().eq(1).all()
    assert frame.groupby("scenario_id").size().eq(3).all()
    assert frame["Document"].map(text_hash).is_unique
    with pytest.raises(ValueError, match="Topic_group"):
        validate_frame(frame, list(SCENARIOS), set())


def prepare_stress(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    bundle = root / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text("{}")
    manifest: dict[str, Any] = {"labels": list(SCENARIOS), "models": {}, "files": {}}
    monkeypatch.setattr(synthetic_stress, "verify_bundle", lambda _: manifest)
    monkeypatch.setattr(synthetic_stress, "original_text_hashes", lambda _: set())
    output = root / "stress"
    synthetic_stress.generate(output, bundle)
    return output, bundle


def test_generated_plan_explicitly_disclaims_real_independence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, _ = prepare_stress(tmp_path, monkeypatch)
    plan = json.loads((output / "stress_plan.json").read_text())
    assert plan["independent_real_world_evidence"] is False
    assert plan["variants_are_correlated"] is True
    assert plan["no_threshold_search"] is True


def test_stress_cases_cannot_be_edited_after_freeze(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, bundle = prepare_stress(tmp_path, monkeypatch)
    path = output / "synthetic_cases.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="changed after plan"):
        synthetic_stress.evaluate(output, bundle)
