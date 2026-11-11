"""Bind a prediction CSV to the exact model bundle that generated it."""

import json
from pathlib import Path
from typing import Any

from src.hashing import calculate_file_sha256


def cnn_bundle_hashes(model_path: Path) -> dict[str, str]:
    return {name: calculate_file_sha256(model_path.parent / name)
            for name in (model_path.name, "vocab.json", "labels.json", "config.json")}


def provenance_path(predictions_path: Path) -> Path:
    return predictions_path.with_suffix(".provenance.json")


def write_prediction_provenance(
    predictions_path: Path, model_path: Path, initial_bundle: dict[str, str],
) -> None:
    if cnn_bundle_hashes(model_path) != initial_bundle:
        raise RuntimeError("CNN bundle changed during prediction; refusing provenance")
    record = {"schema_version": 1, "model_sha256": initial_bundle[model_path.name],
              "bundle_sha256": initial_bundle,
              "predictions_sha256": calculate_file_sha256(predictions_path)}
    provenance_path(predictions_path).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n",
    )


def validate_prediction_provenance(predictions_path: Path, model_path: Path) -> str:
    try:
        record: Any = json.loads(provenance_path(predictions_path).read_text(encoding="utf-8"))
        bundle = cnn_bundle_hashes(model_path)
        if (not isinstance(record, dict) or record.get("schema_version") != 1
                or record.get("bundle_sha256") != bundle
                or record.get("model_sha256") != bundle[model_path.name]
                or record.get("predictions_sha256") != calculate_file_sha256(predictions_path)):
            raise ValueError("prediction/model/bundle mismatch")
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(
            "Missing, malformed or stale prediction provenance; rerun evaluate_cnn "
            "with the intended model bundle"
        ) from exc
    return bundle[model_path.name]
