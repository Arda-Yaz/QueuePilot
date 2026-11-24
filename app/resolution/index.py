"""Versioned local support index shared by lexical and dense retrieval."""

import argparse
import hashlib
import json
import math
import re
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

import numpy as np

CORPUS = Path(__file__).resolve().parents[2] / "support" / "corpus"
DENSE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DENSE_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
DENSE_VERSION = f"{DENSE_MODEL}@{DENSE_REVISION}"
CHUNKING = "heading-paragraph-v1"
MAX_PASSAGE_CHARS = 1000
MAX_CONTEXT_CHARS = 3500
DEFAULT_K = 3
MIN_SHARED_TERMS = 2
BM25_K1 = 1.2
BM25_B = 0.75
Method = Literal["lexical", "dense"]
STOP_WORDS = frozenset(
    "a an and are as at be can could do does for from how i in is it me my of on or "
    "should the this to was what when where which with would you your "
    "ama ben bir bu da de en icin ile mi mu nasil ne nerede su ve veya".split()
)


@dataclass(frozen=True)
class Passage:
    id: str
    document_id: str
    title: str
    section: str
    text: str
    url: str | None

    def context(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "section": self.section, "text": self.text}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_corpus(directory: Path) -> list[Passage]:
    passages = []
    for path in sorted(directory.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        header, *sections = re.split(r"(?m)^## ", content)
        match = re.fullmatch(r"# ([^\n]+)(?:\nSource: (https://[^\s]+))?\s*", header)
        if not match or not sections or not re.fullmatch(r"[a-z0-9-]+", path.stem):
            raise ValueError(f"Invalid document header: {path.name}")
        title, url = match.groups()
        keys = set()
        for section in sections:
            heading, _, body = section.partition("\n")
            match = re.fullmatch(r"\[([a-z0-9-]+)\] (.+)", heading)
            if not match or not body.strip():
                raise ValueError(f"Invalid section: {path.name}")
            key, label = match.groups()
            if key in keys:
                raise ValueError(f"Repeated section identifier: {path.name}")
            keys.add(key)
            for ordinal, paragraph in enumerate(re.split(r"\n\s*\n", body.strip()), 1):
                text = paragraph.strip()
                if len(text) > MAX_PASSAGE_CHARS:
                    raise ValueError(f"Split long paragraph at an authoring boundary: {path.name}")
                passages.append(Passage(f"{path.stem}:{key}:{ordinal}", path.stem,
                                        title, label, text, url))
    if not passages:
        raise ValueError("The support corpus is empty.")
    return passages


def _embedder() -> Any:
    try:
        snapshot_download = import_module("huggingface_hub").snapshot_download
        model_cls = import_module("sentence_transformers").SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install requirements/suggestion/dense.txt and run download-model.") from exc
    # Pass a local directory so tokenizer helpers do not perform Hub metadata requests.
    snapshot = snapshot_download(DENSE_MODEL, revision=DENSE_REVISION, local_files_only=True)
    return model_cls(
        snapshot, device="cpu", local_files_only=True,
        trust_remote_code=False, model_kwargs={"use_safetensors": True},
    )


def download_model() -> None:
    try:
        snapshot_download = import_module("huggingface_hub").snapshot_download
    except ImportError as exc:
        raise RuntimeError("Install requirements/suggestion/dense.txt first.") from exc
    snapshot_download(
        DENSE_MODEL, revision=DENSE_REVISION,
        allow_patterns=["*.json", "1_Pooling/config.json", "model.safetensors", "sentencepiece.bpe.model"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )


def build_index(directory: Path, output: Path, *, dense: bool = False) -> str:
    passages = read_corpus(directory)
    records = [asdict(passage) for passage in passages]
    version = _digest({"chunking": CHUNKING, "passages": records})
    payload: dict[str, Any] = {"version": version, "chunking": CHUNKING, "passages": records}
    if dense:
        model = _embedder()
        payload["dense_version"] = DENSE_VERSION
        payload["vectors"] = model.encode(
            [_search_text(passage) for passage in passages], normalize_embeddings=True
        ).tolist()
    output.parent.mkdir(parents=True, exist_ok=True)
    file = tempfile.NamedTemporaryFile(dir=output.parent, encoding="utf-8", mode="w",
                                       delete=False)
    temporary = Path(file.name)
    try:
        with file:
            json.dump(payload, file, ensure_ascii=False, allow_nan=False)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return version


def _search_text(passage: Passage) -> str:
    return f"{passage.title}\n{passage.section}\n{passage.text}"


def _terms(text: str) -> list[str]:
    # Match Turkish dotted/dotless I and accent-free ticket spelling consistently.
    folded = unicodedata.normalize("NFKD", text.casefold().replace("ı", "i"))
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return [term for term in re.findall(r"[^\W_]+", plain)
            if len(term) > 1 and term not in STOP_WORDS]


class SupportIndex:
    def __init__(self, path: Path, method: Method) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload["passages"]
        self.version = _digest({"chunking": CHUNKING, "passages": records})
        if payload["chunking"] != CHUNKING or payload["version"] != self.version:
            raise ValueError("Support index version mismatch. Rebuild the index.")
        self.method = method
        self.passages = [Passage(**record) for record in records]
        self.counts = [Counter(_terms(_search_text(passage))) for passage in self.passages]
        self.terms_by_id = {passage.id: frozenset(counts)
                            for passage, counts in zip(self.passages, self.counts, strict=True)}
        if not self.passages or len(self.terms_by_id) != len(self.passages):
            raise ValueError("Support index must have unique passages.")
        self.lengths = [counts.total() for counts in self.counts]
        self.avg_length = sum(self.lengths) / len(self.lengths)
        frequencies = Counter(term for counts in self.counts for term in counts)
        self.idf = {term: math.log1p((len(records) - count + 0.5) / (count + 0.5))
                    for term, count in frequencies.items()}
        self.model: Any = None
        self.vectors = None
        if method == "dense":
            if payload.get("dense_version") != DENSE_VERSION:
                raise ValueError("Build the support index with --dense.")
            vectors = np.asarray(payload["vectors"], dtype=np.float32)
            if vectors.shape != (len(records), 384) or not np.isfinite(vectors).all():
                raise ValueError("Invalid dense support vectors.")
            self.vectors = vectors
            self.model = _embedder()

    def settings(self) -> dict[str, object]:
        return {"method": self.method, "chunking": CHUNKING, "k": DEFAULT_K,
                "max_context_chars": MAX_CONTEXT_CHARS, "min_shared_terms": MIN_SHARED_TERMS,
                "bm25": {"k1": BM25_K1, "b": BM25_B} if self.method == "lexical" else None,
                "embedding_model": DENSE_VERSION if self.method == "dense" else None}

    def rank(self, ticket: str, k: int) -> list[Passage]:
        scores: list[float]
        if self.vectors is not None:
            query = self.model.encode([ticket], normalize_embeddings=True)[0]
            scores = (self.vectors @ query).tolist()
        else:
            terms = sorted(set(_terms(ticket)))
            scores = []
            for counts, length in zip(self.counts, self.lengths, strict=True):
                norm = BM25_K1 * (1 - BM25_B + BM25_B * length / self.avg_length)
                scores.append(sum(self.idf[term] * counts[term] * (BM25_K1 + 1)
                                  / (counts[term] + norm) for term in terms if term in counts))
        ranked = sorted(zip(self.passages, scores, strict=True),
                        key=lambda pair: (-pair[1], pair[0].id))
        return [passage for passage, score in ranked if self.method == "dense" or score > 0][:k]

    def context(self, ticket: str, ranked: Sequence[Passage]) -> list[Passage]:
        terms = set(_terms(ticket))
        selected: list[Passage] = []
        serialized: list[dict[str, str]] = []
        for passage in ranked:
            if len(terms & self.terms_by_id[passage.id]) < MIN_SHARED_TERMS:
                continue
            candidate = passage.context()
            if len(json.dumps([*serialized, candidate], ensure_ascii=False)) <= MAX_CONTEXT_CHARS:
                selected.append(passage)
                serialized.append(candidate)
        return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download-model")
    index = sub.add_parser("index")
    index.add_argument("--corpus", type=Path, default=CORPUS)
    index.add_argument("--output", type=Path, required=True)
    index.add_argument("--dense", action="store_true")
    args = parser.parse_args()
    if args.command == "download-model":
        download_model()
    else:
        print(build_index(args.corpus, args.output, dense=args.dense))


if __name__ == "__main__":
    main()
