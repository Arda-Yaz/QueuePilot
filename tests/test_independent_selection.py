"""Five-way partition and checkpoint-frozen backend selection contracts."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from src import select_model
from src.data import validate_persisted_splits
from src.freeze_backend import choose_backend
from src.prepare_data import split_checkpoint_risk


def test_checkpoint_risk_subdivision_is_reproducible_and_exhaustive() -> None:
    frame = pd.DataFrame({"Topic_group": ["A", "B"] * 50}, index=range(100))
    checkpoint, risk = split_checkpoint_risk(frame)
    again, _ = split_checkpoint_risk(frame)
    assert checkpoint.equals(again)
    assert set(checkpoint.index).isdisjoint(risk.index)
    assert set(checkpoint.index) | set(risk.index) == set(frame.index)
    assert len(checkpoint) == len(risk) == 50


@pytest.mark.parametrize("problem", ["none", "overlap", "missing"])
def test_five_way_validator(problem: str) -> None:
    df = pd.DataFrame(index=list("abcde"))
    manifest = {"dataset_sha256": "sha", "total_rows": 5,
                "protocol_version": 2, "checkpoint_rows": 1}
    checkpoint = pd.Index(["d" if problem == "overlap" else "e"])
    with patch("src.data.calculate_file_sha256", return_value="sha"):
        args = (df, pd.Index(["a"]), pd.Index(["b"]), pd.Index(["c"]), manifest,
                pd.Index(["d"]), None if problem == "missing" else checkpoint)
        if problem == "none":
            validate_persisted_splits(*args)
        else:
            with pytest.raises(RuntimeError):
                validate_persisted_splits(*args)


def test_backend_choice_uses_checkpoint_f1_and_prefers_baseline_on_ties() -> None:
    assert choose_backend({"baseline": 0.8, "cnn": 0.9}) == "cnn"
    assert choose_backend({"baseline": 0.9, "cnn": 0.9}) == "baseline"


def test_risk_failure_cannot_switch_frozen_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "params.yaml").write_text("routing: {target_accuracy: 0.9}")
    (tmp_path / "frozen_backend.json").write_text(json.dumps(
        {"selected_backend": "baseline", "selected_model_sha256": "sha"}))
    monkeypatch.setattr(select_model, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(select_model, "METRICS_DIR", tmp_path)
    with patch.object(select_model, "load_candidate", return_value={
        "model_sha256": "sha", "validation_accuracy_ci_lower": 0.8,
    }) as loader:
        with pytest.raises(RuntimeError, match="no risk-driven"):
            select_model.main()
        assert loader.call_count == 1
        assert loader.call_args.args[0] == "baseline"
    assert not (tmp_path / "model_selection.json").exists()


def test_dvc_freezes_before_risk_and_tracks_checkpoint_ids() -> None:
    stages = yaml.safe_load(Path("dvc.yaml").read_text())["stages"]
    assert all("tune_predictions" not in dep for dep in stages["freeze_backend"]["deps"])
    for backend in ("baseline", "cnn"):
        assert "reports/metrics/frozen_backend.json" in stages[f"analyze_threshold_{backend}"]["deps"]
        assert "reports/data/checkpoint_ids.csv" in stages[f"train_{backend}"]["deps"]
