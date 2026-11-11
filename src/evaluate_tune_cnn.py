"""Evaluate the TextCNN model on the tune set.

Produces:
- Tune-set predictions CSV (used by threshold selection)
- Tune-set calibration metrics (ECE, Brier score)

Note: these calibration metrics are measured on the TUNE set â€” the same
partition used for threshold selection.  For held-out calibration quality
assessment on the independent CALIBRATION partition, see
``evaluate_calibration_cnn.py``.
"""

import json

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.cnn_data import TicketDataset
from src.cnn_evaluation import predict_batches
from src.data import load_data, load_splits
from src.evaluate import build_prediction_frame, calculate_calibration_metrics, calculate_metrics
from src.hashing import calculate_file_sha256
from src.paths import CNN_MODEL_PATH, METRICS_DIR, ROOT_DIR
from src.textcnn import TextCNN

CNN_DIR = ROOT_DIR / "artifacts" / "cnn"


def main(partition: str = "tune") -> None:
    with open(CNN_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab = json.load(f)

    with open(CNN_DIR / "labels.json", "r", encoding="utf-8") as f:
        labels = json.load(f)

    with open(CNN_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    df = load_data()
    splits = load_splits(df)
    tune_df = splits.tune if partition == "tune" else splits.checkpoint
    if tune_df is None:
        raise RuntimeError("Checkpoint partition missing")

    label_to_id = {label: index for index, label in enumerate(labels)}
    y_tune = [label_to_id[label] for label in tune_df["Topic_group"]]

    tune_dataset = TicketDataset(
        texts=tune_df["Document"].tolist(),
        labels=y_tune,
        vocab=vocab,
        max_length=int(config["max_length"]),
    )

    tune_loader = DataLoader(
        tune_dataset,
        batch_size=64,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    model = TextCNN(
        vocab_size=len(vocab),
        embedding_dim=config["embedding_dim"],
        num_filters=config["num_filters"],
        kernel_sizes=config["kernel_sizes"],
        num_classes=config["num_classes"],
        dropout=config["dropout"],
    ).to(device)

    state_dict = torch.load(
        CNN_DIR / "textcnn.pt",
        map_location=device,
        weights_only=True,
    )
    model.load_state_dict(state_dict)
    model.eval()

    all_predictions, all_confidences = predict_batches(model, tune_loader, device)

    true_labels = [labels[index] for index in y_tune]
    predicted_labels = [labels[index] for index in all_predictions]

    tune_metrics = calculate_metrics(true_labels, np.asarray(predicted_labels))
    with open(METRICS_DIR / f"cnn_{partition}_metrics.json", "w", encoding="utf-8") as f:
        json.dump({**tune_metrics, "model_sha256": calculate_file_sha256(CNN_MODEL_PATH)}, f, indent=4)

    calib_metrics = calculate_calibration_metrics(
        y_true_labels=true_labels,
        y_pred_labels=np.asarray(predicted_labels),
        y_confidence=np.asarray(all_confidences),
    )
    with open(METRICS_DIR / f"cnn_{partition}_calibration_metrics.json", "w", encoding="utf-8") as f:
        json.dump({**calib_metrics, "model_sha256": calculate_file_sha256(CNN_MODEL_PATH)}, f, indent=4)

    print("\nCNN Tune Metrics")
    for key, value in tune_metrics.items():
        print(f"{key}: {value:.4f}")

    print("\nCalibration Quality (tune set):")
    print(f"Brier score: {calib_metrics['top_label_brier_score']:.6f}")
    print(f"Expected Calibration Error (ECE): {calib_metrics['expected_calibration_error']:.6f}")

    results = build_prediction_frame(
        tune_df.index.to_numpy(), true_labels,
        predicted_labels, all_confidences,
    )

    output_path = METRICS_DIR / f"cnn_{partition}_predictions.csv"
    results.to_csv(output_path, index=False)

    print(f"Saved tune predictions to: {output_path}")
    print("Tune accuracy:", results["correct"].mean())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", choices=["tune", "checkpoint"], default="tune")
    main(parser.parse_args().partition)
