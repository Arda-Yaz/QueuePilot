"""Qualify a pinned human-labeled corpus without inventing a label mapping."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.independent_data import original_text_hashes, text_hash
from src.hashing import calculate_file_sha256
from src.paths import DATA_PATH, ROOT_DIR

RECORD = "7384758"
CHECKSUMS = {
    "X_train.csv": "0a79f0c2f95fcdb407f24b2c0ad7f7d1",
    "X_test.csv": "02328c4e09a78a41acb22ce17e6e0312",
    "y_train.csv": "90876921486a26a67bc1976da87305d9",
    "y_test.csv": "2f054c0e3d8cbbbd76adf30d13a7710a",
}


def load_pinned_corpus(directory: Path) -> pd.DataFrame:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    if str(metadata["id"]) != RECORD or metadata["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Unexpected dataset record or license")
    reported = {item["key"]: item["checksum"] for item in metadata["files"]}
    for name, checksum in CHECKSUMS.items():
        if reported[name] != f"md5:{checksum}" or hashlib.md5((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Pinned source checksum mismatch: {name}")
    partitions = []
    for split in ("train", "test"):
        texts = pd.read_csv(directory / f"X_{split}.csv", dtype=str, keep_default_na=False)
        labels = pd.read_csv(directory / f"y_{split}.csv", dtype=str, keep_default_na=False)
        if set(texts["id"]) != set(labels["id"]):
            raise ValueError("Source text/label ID mismatch")
        joined = texts.merge(labels, on="id", validate="one_to_one")
        joined["source_split"] = split
        partitions.append(joined)
    return pd.concat(partitions, ignore_index=True)


def qualification(frame: pd.DataFrame, known: set[str], schema: list[str]) -> dict[str, Any]:
    hashes = frame["text"].map(text_hash)
    counts = frame["category_truth"].value_counts().to_dict()
    incompatible = sorted(set(counts) - set(schema))
    tagged = frame.assign(text_sha256=hashes)
    shared = set(tagged.loc[tagged["source_split"] == "train", "text_sha256"]) & set(
        tagged.loc[tagged["source_split"] == "test", "text_sha256"])
    return {
        "rows": len(frame), "source_label_counts": counts,
        "source_id_duplicates": int(frame["id"].duplicated().sum()),
        "normalized_text_duplicates": int(hashes.duplicated().sum()),
        "unique_normalized_texts": int(hashes.nunique()),
        "conflicting_label_text_groups": int((tagged.groupby("text_sha256")["category_truth"].nunique() > 1).sum()),
        "source_train_test_shared_normalized_texts": len(shared),
        "source_split_counts": frame["source_split"].value_counts().to_dict(),
        "blank_texts": int(frame["text"].str.strip().eq("").sum()),
        "exact_normalized_overlap_with_original": int(hashes.isin(known).sum()),
        "unsupported_labels": incompatible,
        "label_mapping_applied": False,
        "compatible_with_full_eight_class_audit": not incompatible and set(counts) == set(schema),
        "source_train_test_names_do_not_refer_to_queuepilot_partitions": True,
        "independence_limit": "Distinct provenance and normalized exact-text check; near-duplicate and taxonomy equivalence not proven",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT_DIR / f"reports/private/external/zenodo-{RECORD}")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "reports/validation/2026-11-12/public_source_qualification.json")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        args.source.mkdir(parents=True, exist_ok=True)
        for name in ("metadata.json", *CHECKSUMS):
            url = (f"https://zenodo.org/api/records/{RECORD}" if name == "metadata.json" else
                   f"https://zenodo.org/records/{RECORD}/files/{name}?download=1")
            req = urllib.request.Request(url, headers={"User-Agent": "QueuePilot dataset qualification"})
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
            (args.source / name).write_bytes(raw)
    frame = load_pinned_corpus(args.source)
    schema = json.loads((ROOT_DIR / "reports/development/2026-11-12/frozen_candidate_manifest.json").read_text())["labels"]
    result = qualification(frame, original_text_hashes(DATA_PATH), schema)
    result.update({
        "source": f"https://zenodo.org/records/{RECORD}", "doi": f"10.5281/zenodo.{RECORD}",
        "author": "Leonardo Santiago Benitez Pereira", "license": "CC-BY-4.0",
        "publisher_description": "2229 real IT tickets classified by three IT professionals in 2020; multilingual; anonymized",
        "checksums_sha256": {name: calculate_file_sha256(args.source / name) for name in ("metadata.json", *CHECKSUMS)},
        "metadata_license_checked": True, "model_predictions_used_to_map_labels": False,
        "qualification_source_sha256": calculate_file_sha256(Path(__file__)),
        "original_dataset_sha256": calculate_file_sha256(DATA_PATH),
        "decision": "Do not use as an eight-class risk/audit corpus without a justified taxonomy alignment",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
