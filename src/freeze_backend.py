"""Freeze the backend using checkpoint data before accessing risk predictions."""

import json

import pandas as pd
from sklearn.metrics import f1_score

from src.hashing import calculate_file_sha256
from src.paths import BASELINE_MODEL_PATH, CNN_MODEL_PATH, METRICS_DIR


def choose_backend(scores: dict[str, float]) -> str:
    return max(("baseline", "cnn"), key=lambda name: scores[name])


def main() -> None:
    scores = {}
    for backend in ("baseline", "cnn"):
        frame = pd.read_csv(METRICS_DIR / f"{backend}_checkpoint_predictions.csv")
        scores[backend] = float(f1_score(frame["true_label"], frame["predicted_label"],
                                         average="macro", zero_division=0))
    backend = choose_backend(scores)
    record = {"selection_dataset": "checkpoint", "selection_rule": "macro_f1; baseline wins exact ties",
              "selected_backend": backend, "checkpoint_macro_f1": scores,
              "selected_model_sha256": calculate_file_sha256(
                  BASELINE_MODEL_PATH if backend == "baseline" else CNN_MODEL_PATH)}
    (METRICS_DIR / "frozen_backend.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n",
    )


if __name__ == "__main__":
    main()
