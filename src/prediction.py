"""Backend-independent prediction records and routing presentation."""

from typing import TypedDict

import numpy as np


class TopPrediction(TypedDict):
    category: str
    probability: float


class PredictionResult(TypedDict):
    category: str
    confidence: float
    threshold: float
    needs_manual_review: bool
    top_3: list[TopPrediction]


class CNNConfig(TypedDict):
    max_length: int
    embedding_dim: int
    num_filters: int
    kernel_sizes: list[int]
    num_classes: int
    dropout: float
    training_truncation_rate: float
    p50: float
    p90: float
    p95: float
    p99: float


def format_prediction(
    labels: "np.ndarray | list[str]",
    probabilities: "np.ndarray",
    threshold: float,
) -> PredictionResult:
    order = np.argsort(probabilities)[::-1]
    best_index = int(order[0])
    confidence = float(probabilities[best_index])

    top_3: list[TopPrediction] = [
        {"category": str(labels[i]), "probability": float(probabilities[i])}
        for i in order[:3]
    ]

    return {
        "category": str(labels[best_index]),
        "confidence": confidence,
        "threshold": threshold,
        "needs_manual_review": confidence < threshold,
        "top_3": top_3,
    }


