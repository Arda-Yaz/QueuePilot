"""Operator-only suggestion workflow, validation and SQLite idempotency."""

import asyncio
import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, Field, ValidationError

from app.resolution.index import DEFAULT_K, Method, Passage, SupportIndex
from app.resolution.provider import (
    PROMPT_VERSION,
    DraftProvider,
    FakeProvider,
    ModelDraft,
    OpenAIProvider,
    TokenUsage,
)

TOTAL_TIMEOUT = 10.0
PROVIDER_TIMEOUT = 7.0
DB_RESERVE = 1.0
LEASE_SECONDS = 30.0
ReviewReason = Literal[
    "insufficient_evidence", "provider_timeout", "provider_error", "invalid_output",
    "provider_abstained", "request_timeout", "retrieval_unavailable", "interrupted", "in_progress",
]


class ResolutionSource(BaseModel):
    id: str
    document_id: str
    title: str
    section: str
    url: str | None


class ResolutionResult(BaseModel):
    operation_id: str
    status: Literal["draft_ready", "needs_review", "in_progress"]
    review_reason: ReviewReason | None = None
    draft: str | None = None
    sources: list[ResolutionSource] = Field(default_factory=list)
    retrieval_ms: float = 0
    total_ms: float = 0
    usage: TokenUsage | None = None


class IdempotencyConflict(Exception):
    pass


class RetrievalBusy(Exception):
    pass


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class OperationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS resolution_operations (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    corpus_version TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    selected_ids TEXT NOT NULL DEFAULT '[]',
                    result TEXT,
                    UNIQUE (scope, idempotency_key)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=0.25)

    def claim(self, scope: str, key: str, ticket: str, corpus_version: str,
              configuration: str) -> tuple[str, ResolutionResult | None]:
        fingerprint = _fingerprint(ticket)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT id, fingerprint, expires_at, result FROM resolution_operations
                WHERE scope = ? AND idempotency_key = ?
            """, (_fingerprint(scope), key)).fetchone()
            now = time.time()
            if row is None:
                operation_id = str(uuid.uuid4())
                db.execute("""
                    INSERT INTO resolution_operations
                        (id, scope, idempotency_key, fingerprint, status, expires_at,
                         corpus_version, configuration)
                    VALUES (?, ?, ?, ?, 'in_progress', ?, ?, ?)
                """, (operation_id, _fingerprint(scope), key, fingerprint, now + LEASE_SECONDS,
                      corpus_version, configuration))
                return operation_id, None
            operation_id, saved_fingerprint, expires_at, result = row
            if saved_fingerprint != fingerprint:
                raise IdempotencyConflict
            if result is not None:
                return operation_id, ResolutionResult.model_validate_json(result)
            if expires_at > now:
                return operation_id, ResolutionResult(
                    operation_id=operation_id, status="in_progress", review_reason="in_progress",
                )
            interrupted = ResolutionResult(operation_id=operation_id, status="needs_review",
                                           review_reason="interrupted")
            self._write_result(db, interrupted, [])
            return operation_id, interrupted

    @staticmethod
    def _write_result(db: sqlite3.Connection, result: ResolutionResult,
                      selected_ids: list[str]) -> None:
        db.execute("""
            UPDATE resolution_operations SET status = ?, selected_ids = ?, result = ?
            WHERE id = ?
        """, (result.status, json.dumps(selected_ids), result.model_dump_json(),
              result.operation_id))

    def finish(self, result: ResolutionResult, selected_ids: list[str]) -> ResolutionResult:
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT expires_at, result FROM resolution_operations WHERE id = ?",
                             (result.operation_id,)).fetchone()
            if row is None:
                raise sqlite3.OperationalError("Suggestion operation is missing")
            expires_at, saved = row
            if saved is not None:
                return ResolutionResult.model_validate_json(saved)
            if expires_at <= time.time():
                result = ResolutionResult(operation_id=result.operation_id, status="needs_review",
                                          review_reason="interrupted")
            self._write_result(db, result, selected_ids)
            return result


class ResolutionService:
    def __init__(self, index: SupportIndex, store: OperationStore, provider: DraftProvider) -> None:
        self.index = index
        self.store = store
        self.provider = provider
        self._retrieval_slot = threading.Lock()
        self.configuration = {
            "corpus_version": index.version, "retriever": index.settings(),
            "provider": provider.name, "model": provider.model_version, "prompt": PROMPT_VERSION,
            "total_timeout_s": TOTAL_TIMEOUT, "provider_timeout_s": PROVIDER_TIMEOUT,
        }

    def _select(self, ticket: str) -> list[Passage]:
        if self.index.method == "lexical":
            return self.index.context(ticket, self.index.rank(ticket, DEFAULT_K))
        if not self._retrieval_slot.acquire(blocking=False):
            raise RetrievalBusy
        try:
            return self.index.context(ticket, self.index.rank(ticket, DEFAULT_K))
        finally:
            self._retrieval_slot.release()

    async def suggest(self, ticket: str, scope: str, key: str) -> ResolutionResult:
        start = time.perf_counter()
        request_deadline = start + TOTAL_TIMEOUT
        deadline = request_deadline - DB_RESERVE
        async with asyncio.timeout(max(0, deadline - time.perf_counter())):
            operation_id, existing = await asyncio.to_thread(
                self.store.claim, scope, key, ticket, self.index.version,
                json.dumps(self.configuration, sort_keys=True),
            )
        if existing is not None:
            return existing
        result = ResolutionResult(operation_id=operation_id, status="needs_review")
        selected: list[Passage] = []
        retrieval_start = time.perf_counter()
        try:
            async with asyncio.timeout(max(0, deadline - time.perf_counter())):
                selected = await asyncio.to_thread(self._select, ticket)
        except TimeoutError:
            result.review_reason = "request_timeout"
        except Exception:
            result.review_reason = "retrieval_unavailable"
        result.retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
        if result.review_reason is None:
            if not selected:
                result.review_reason = "insufficient_evidence"
            else:
                await self._generate(result, ticket, selected, deadline)
        result.total_ms = (time.perf_counter() - start) * 1000
        async with asyncio.timeout(max(0, request_deadline - time.perf_counter())):
            return await asyncio.to_thread(
                self.store.finish, result, [passage.id for passage in selected],
            )

    async def _generate(self, result: ResolutionResult, ticket: str, selected: list[Passage],
                        deadline: float) -> None:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            result.review_reason = "request_timeout"
            return
        try:
            async with asyncio.timeout(min(PROVIDER_TIMEOUT, remaining)):
                output = await self.provider.generate(ticket, selected)
        except TimeoutError:
            result.review_reason = ("provider_timeout" if remaining >= PROVIDER_TIMEOUT
                                    else "request_timeout")
            return
        except Exception:
            result.review_reason = "provider_error"
            return
        result.usage = output.usage
        try:
            generated = ModelDraft.model_validate_json(output.content)
        except ValidationError:
            result.review_reason = "invalid_output"
            return
        draft = generated.draft.strip()
        ids = generated.source_ids
        allowed = {passage.id: passage for passage in selected}
        if not draft and not ids:
            result.review_reason = "provider_abstained"
        elif not draft or not ids or len(set(ids)) != len(ids) or any(i not in allowed for i in ids):
            result.review_reason = "invalid_output"
        else:
            result.status = "draft_ready"
            result.draft = draft
            result.sources = [
                ResolutionSource(id=p.id, document_id=p.document_id, title=p.title,
                                 section=p.section, url=p.url)
                for p in (allowed[i] for i in ids)
            ]


def configured_provider(mode: str) -> DraftProvider:
    if mode == "fake":
        return FakeProvider()
    if mode != "openai":
        raise ValueError("SUGGEST_PROVIDER must be fake or openai.")
    model, key = os.getenv("SUGGEST_OPENAI_MODEL"), os.getenv("SUGGEST_OPENAI_API_KEY")
    if not model or not key:
        raise ValueError("SUGGEST_OPENAI_MODEL and SUGGEST_OPENAI_API_KEY are required.")
    return OpenAIProvider(model, key)


def service_from_env(*, api_key_configured: bool) -> ResolutionService | None:
    mode = os.getenv("SUGGEST_PROVIDER")
    if not mode:
        return None
    index = os.getenv("SUGGEST_INDEX")
    database = os.getenv("SUGGEST_DB")
    retriever = os.getenv("SUGGEST_RETRIEVER", "lexical")
    if not index or not database:
        raise ValueError("SUGGEST_INDEX and SUGGEST_DB are required.")
    if retriever != "lexical" and retriever != "dense":
        raise ValueError("SUGGEST_RETRIEVER must be lexical or dense.")
    # The same shared credential that gates /predict must protect external generation.
    if mode == "openai" and not api_key_configured:
        raise ValueError("API_KEY is required when SUGGEST_PROVIDER=openai.")
    provider = configured_provider(mode)
    return ResolutionService(SupportIndex(Path(index), cast(Method, retriever)),
                             OperationStore(Path(database)), provider)
