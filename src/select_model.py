"""Publish the checkpoint-frozen backend with its independent risk threshold.

Legacy select_candidate remains only for historical compatibility. The production
entry point never ranks backends using risk coverage and never accesses test.
"""

import json
from pathlib import Path
from typing import TypedDict

import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, f1_score

from src.paths import METRICS_DIR, ROOT_DIR


class CandidateResult(TypedDict):
    backend: str
    validation_accuracy: float
    validation_macro_f1: float
    threshold: float
    validation_coverage: float
    validation_auto_routed_accuracy: float
    validation_accuracy_ci_lower: float
    model_sha256: str


class ModelPaths(TypedDict):
    predictions: Path
    threshold: Path


MODEL_CONFIGS: dict[str, ModelPaths] = {
    "baseline": {
        "predictions": METRICS_DIR / "baseline_tune_predictions.csv",
        "threshold": METRICS_DIR / "baseline_selected_threshold.json",
    },
    "cnn": {
        "predictions": METRICS_DIR / "cnn_tune_predictions.csv",
        "threshold": METRICS_DIR / "selected_threshold.json",
    },
}


def load_candidate(backend: str, paths: ModelPaths) -> CandidateResult:
    predictions_path = paths["predictions"]
    threshold_path = paths["threshold"]

    if not predictions_path.exists():
        raise FileNotFoundError(f"Validation predictions not found: {predictions_path}")
    if not threshold_path.exists():
        raise FileNotFoundError(f"Threshold config not found: {threshold_path}")

    predictions = pd.read_csv(predictions_path)
    with open(threshold_path, encoding="utf-8") as f:
        threshold = json.load(f)

    ci_lower: float | None = threshold.get("validation_accuracy_ci_lower")
    if ci_lower is None:
        raise RuntimeError(
            f"{backend} threshold artifact does not contain validation_accuracy_ci_lower. "
            "Run threshold analysis again."
        )

    return {
        "backend": backend,
        "validation_accuracy": float(
            accuracy_score(predictions["true_label"], predictions["predicted_label"])
        ),
        "validation_macro_f1": float(
            f1_score(
                predictions["true_label"],
                predictions["predicted_label"],
                average="macro",
                zero_division=0,
            )
        ),
        "threshold": float(threshold["threshold"]),
        "validation_coverage": float(threshold["validation_coverage"]),
        "validation_auto_routed_accuracy": float(threshold["validation_auto_routed_accuracy"]),
        "validation_accuracy_ci_lower": float(ci_lower),
        "model_sha256": threshold["model_sha256"],
    }


def select_candidate(
    candidates: list[CandidateResult], target_accuracy: float,
    min_coverage_improvement: float = 0.0,
) -> CandidateResult:
    """Choose by coverage, then macro F1, after the original risk gate."""
    eligible = [c for c in candidates if c["validation_accuracy_ci_lower"] >= target_accuracy]

    if not eligible:
        raise RuntimeError(
            "No model satisfies the routing requirement: "
            f"lower 95% accuracy CI >= {target_accuracy:.0%}.\n"
            "Candidates:\n"
            + "\n".join(
                f"  {c['backend']}: ci_lower={c['validation_accuracy_ci_lower']:.4f}"
                for c in candidates
            )
        )

    baseline = next((c for c in eligible if c["backend"] == "baseline"), None)
    cnn = next((c for c in eligible if c["backend"] == "cnn"), None)
    if baseline is not None and cnn is not None and min_coverage_improvement > 0:
        if cnn["validation_coverage"] < baseline["validation_coverage"] + min_coverage_improvement:
            return baseline
    return max(
        eligible,
        key=lambda c: (c["validation_coverage"], c["validation_macro_f1"]),
    )


def main() -> None:
    with open(ROOT_DIR / "params.yaml", encoding="utf-8") as f:
        params = yaml.safe_load(f).get("routing", {})

    target_accuracy: float = float(params.get("target_accuracy", 0.90))

    frozen = json.loads((METRICS_DIR / "frozen_backend.json").read_text(encoding="utf-8"))
    backend = frozen["selected_backend"]
    winner = load_candidate(backend, MODEL_CONFIGS[backend])
    if winner["model_sha256"] != frozen["selected_model_sha256"]:
        raise RuntimeError("Frozen backend/model hash mismatch")
    if winner["validation_accuracy_ci_lower"] < target_accuracy:
        raise RuntimeError("Frozen backend fails risk target; no risk-driven backend fallback allowed")
    output: dict[str, object] = {
        "selection_dataset": "checkpoint (backend); independent risk/tune (threshold)",
        "target_accuracy": target_accuracy,
        "selection_rule": "Freeze checkpoint macro-F1 winner, then select its risk threshold; no fallback",
        "selected_backend": backend,
        "selected_threshold": winner["threshold"],
        "selected_model_sha256": winner["model_sha256"],
        "frozen_backend": frozen,
        "candidates": [winner],
    }

    output_path = METRICS_DIR / "model_selection.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    print(f"Selected backend:   {winner['backend']}")
    print(f"Selected threshold: {winner['threshold']}")
    print(f"Tune coverage:      {winner['validation_coverage']:.2%}")
    print(f"CI lower bound:     {winner['validation_accuracy_ci_lower']:.4f} "
          f"(target: >= {target_accuracy:.2f})")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
