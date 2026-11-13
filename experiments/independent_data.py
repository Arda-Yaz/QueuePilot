"""Strict intake for genuinely new, independently labeled ticket batches."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.ticket_text import normalize_text


def text_hash(text: str) -> str:
    """Exclude the label: relabeling an old ticket cannot make it new data."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def original_text_hashes(path: Path) -> set[str]:
    # Only original text is needed; do not open historical evaluation labels.
    return {text_hash(str(text)) for chunk in pd.read_csv(path, usecols=["Document"], chunksize=10000)
            for text in chunk["Document"].dropna()}


def validate_attestation(record: dict[str, Any]) -> None:
    for key in ("not_previously_used", "labels_blind_to_model_predictions"):
        if record.get(key) is not True:
            raise ValueError(f"Independent data requires an explicit true declaration: {key}")
    for key in ("source", "sampling_method", "labeling_process", "collection_window"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"Missing data provenance: {key}")


def validate_frame(
    frame: pd.DataFrame, labels: list[str], forbidden_texts: set[str],
    forbidden_ids: set[str] | None = None,
) -> pd.DataFrame:
    required = {"external_id", "Document", "Topic_group"}
    if not required <= set(frame.columns) or frame.empty:
        raise ValueError("Nonempty CSV requires external_id, Document and Topic_group columns")
    result = frame.copy()
    for name in required:
        if result[name].isna().any() or not result[name].map(lambda x: isinstance(x, str)).all():
            raise ValueError(f"Missing/non-text values in {name}")
        if result[name].str.strip().eq("").any():
            raise ValueError(f"Blank values in {name}")
    result["external_id"] = result["external_id"].str.strip()
    result["Topic_group"] = result["Topic_group"].str.strip()
    if not result["external_id"].is_unique:
        raise ValueError("Duplicate external IDs")
    if not set(result["Topic_group"]) <= set(labels):
        raise ValueError("Unknown class label; use the frozen label schema without renaming")
    hashes = result["Document"].map(text_hash)
    if not hashes.is_unique:
        raise ValueError("Duplicate normalized text within batch, including conflicting labels")
    if set(hashes) & forbidden_texts:
        raise ValueError("Batch overlaps original data or the threshold-selection batch")
    id_hashes = result["external_id"].map(lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest())
    if set(id_hashes) & (forbidden_ids or set()):
        raise ValueError("Audit reuses a threshold-selection external ID")
    result["text_sha256"] = hashes
    result["id_sha256"] = id_hashes
    return result


def load_batch(
    csv_path: Path, attestation_path: Path, labels: list[str], forbidden_texts: set[str],
    forbidden_ids: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    record = json.loads(attestation_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Data provenance must be a JSON object")
    validate_attestation(record)
    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    return validate_frame(frame, labels, forbidden_texts, forbidden_ids), record
