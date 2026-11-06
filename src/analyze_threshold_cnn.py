"""Threshold selection CLI for the CNN backend."""

from src.paths import METRICS_DIR, ROOT_DIR
from src.threshold_analysis import run_threshold_analysis

INPUT_PATH = METRICS_DIR / "cnn_tune_predictions.csv"
OUTPUT_PATH = METRICS_DIR / "threshold_analysis.csv"
THRESHOLD_PATH = METRICS_DIR / "selected_threshold.json"
MODEL_PATH = ROOT_DIR / "artifacts" / "cnn" / "textcnn.pt"



def main() -> None:
    run_threshold_analysis(
        INPUT_PATH, OUTPUT_PATH, THRESHOLD_PATH, MODEL_PATH,
        ROOT_DIR / "params.yaml", "CNN",
    )


if __name__ == "__main__":
    main()
