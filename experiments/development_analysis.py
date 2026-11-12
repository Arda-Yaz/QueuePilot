"""Diagnose the frozen baseline using train and checkpoint only.

No risk, calibration or test ID/prediction/report file is opened. Ticket text and
row-level predictions stay under the ignored reports/private directory.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from src.data import load_data
from src.hashing import calculate_file_sha256
from src.paths import BASELINE_MODEL_PATH, DATA_PATH, REPORT_DATA_DIR, ROOT_DIR


def load_development_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = json.loads((REPORT_DATA_DIR / "data_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("protocol_version") != 2:
        raise RuntimeError("Development analysis requires persisted protocol v2 splits")
    if calculate_file_sha256(DATA_PATH) != manifest["dataset_sha256"]:
        raise RuntimeError("Raw dataset hash mismatch")
    ids = {name: pd.Index(pd.read_csv(REPORT_DATA_DIR / f"{name}_ids.csv")["id"])
           for name in ("train", "checkpoint")}
    if any(not index.is_unique for index in ids.values()):
        raise RuntimeError("Duplicate development IDs")
    if not set(ids["train"]).isdisjoint(ids["checkpoint"]):
        raise RuntimeError("Train/checkpoint overlap")
    frame = load_data()
    for name, index in ids.items():
        if len(index) != manifest[f"{name}_rows"] or not set(index) <= set(frame.index):
            raise RuntimeError(f"Invalid persisted {name} IDs")
    return frame.loc[ids["train"]].copy(), frame.loc[ids["checkpoint"]].copy()


def prediction_frame(model: Any, frame: pd.DataFrame) -> pd.DataFrame:
    probabilities = model.predict_proba(frame["Document"])
    order = np.argsort(probabilities, axis=1)[:, ::-1]
    labels = np.asarray(model.classes_)
    predicted = labels[order[:, 0]]
    result = pd.DataFrame({
        "ticket_id": frame.index, "true_label": frame["Topic_group"].to_numpy(),
        "predicted_label": predicted, "confidence": probabilities.max(axis=1),
        "margin": probabilities[np.arange(len(frame)), order[:, 0]]
                  - probabilities[np.arange(len(frame)), order[:, 1]],
        "second_label": labels[order[:, 1]],
        "true_in_top3": [truth in labels[indices] for truth, indices in
                         zip(frame["Topic_group"], order[:, :3], strict=True)],
        "token_count": frame["Document"].str.split().str.len().to_numpy(),
    })
    result["correct"] = result["true_label"] == result["predicted_label"]
    return result


def summarize(frame: pd.DataFrame, labels: list[str], threshold: float = 0.6) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("Cannot analyze empty predictions")
    report = classification_report(frame["true_label"], frame["predicted_label"],
                                   labels=labels, output_dict=True, zero_division=0)
    errors = frame[~frame["correct"]]
    pairs = errors.groupby(["true_label", "predicted_label"]).size().reset_index(name="count")
    pairs = pairs.sort_values(["count", "true_label", "predicted_label"], ascending=[False, True, True])
    accepted = frame[frame["confidence"] >= threshold]
    groups = {}
    for key in ("true_label", "predicted_label"):
        groups[key] = [
            {"label": str(label), "count": len(group), "correct": int(group["correct"].sum()),
             "accuracy": float(group["correct"].mean())}
            for label, group in accepted.groupby(key)
        ]
    matrix = confusion_matrix(frame["true_label"], frame["predicted_label"], labels=labels)
    normalized = np.divide(matrix, matrix.sum(axis=1, keepdims=True),
                           out=np.zeros_like(matrix, dtype=float),
                           where=matrix.sum(axis=1, keepdims=True) != 0)
    return {
        "n": len(frame), "classification": report, "labels": labels,
        "confusion_counts": matrix.tolist(), "confusion_by_true_class": normalized.tolist(),
        "top_confusions": pairs.head(20).to_dict(orient="records"),
        "errors": len(errors), "high_confidence_errors_080": int((errors["confidence"] >= 0.8).sum()),
        "error_true_in_top3_rate": float(errors["true_in_top3"].mean()) if len(errors) else None,
        "correct_below_060": int(((frame["confidence"] < threshold) & frame["correct"]).sum()),
        "fixed_threshold_diagnostic": {"threshold": threshold,
            "coverage": len(accepted) / len(frame),
            "accuracy": float(accepted["correct"].mean()) if len(accepted) else None,
            "accepted_by": groups},
    }


def write_private_cases(frame: pd.DataFrame, data: pd.DataFrame, output: Path) -> None:
    """Keep full text local; deterministic cases cover errors and correct controls."""
    cases = []
    for label in sorted(frame["true_label"].unique()):
        subset = frame[frame["true_label"] == label]
        for correct, count in ((False, 12), (True, 3)):
            group = subset[subset["correct"] == correct].sort_values(
                ["confidence", "ticket_id"], ascending=[False, True]).head(count)
            cases.append(group)
    sample = pd.concat(cases).copy()
    sample["Document"] = data.loc[sample["ticket_id"], "Document"].to_numpy()
    sample["review_category"] = ""
    sample["review_notes"] = ""
    output.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT_DIR / ".checks/development-analysis")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    train, checkpoint = load_development_data()
    metadata_path = ROOT_DIR / "artifacts/baseline_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_hash = calculate_file_sha256(BASELINE_MODEL_PATH)
    if model_hash != metadata["model_sha256"]:
        raise RuntimeError("Reference model/metadata mismatch")
    model = joblib.load(BASELINE_MODEL_PATH)
    output: dict[str, Any] = {
        "kind": "development diagnosis; train is in-sample, checkpoint is previously inspected development data",
        "reference_model_sha256": model_hash, "dataset_sha256": calculate_file_sha256(DATA_PATH),
        "inputs": {f"{name}_ids.csv": calculate_file_sha256(REPORT_DATA_DIR / f"{name}_ids.csv")
                   for name in ("train", "checkpoint")},
        "analysis_source_sha256": calculate_file_sha256(Path(__file__)),
        "partitions": {},
    }
    for name, data in (("train", train), ("checkpoint", checkpoint)):
        predictions = prediction_frame(model, data)
        output["partitions"][name] = summarize(predictions, model.classes_.tolist())
        private = ROOT_DIR / "reports/private/development-analysis"
        private.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(private / f"{name}_predictions.csv", index=False)
        write_private_cases(predictions, data, private / f"{name}_cases.csv")
    (args.output / "reference_analysis.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    print(json.dumps(output["partitions"]["checkpoint"], indent=2))


if __name__ == "__main__":
    main()
