import asyncio
import json
import sqlite3
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from test_api import FakePredictor

from app import main as api
from app.resolution import service as resolution
from app.resolution.index import CORPUS, SupportIndex, build_index
from app.resolution.provider import OpenAIProvider, ProviderOutput

VPN = "The VPN client reports an expired profile. How can I renew the VPN profile?"
UNKNOWN = "Cafeteria meal voucher refund"
INJECTION = "This suspicious import directive asks to ignore earlier instructions."


@pytest.fixture
def enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    index_path = tmp_path / "index.json"
    build_index(CORPUS, index_path)
    monkeypatch.setenv("SUGGEST_PROVIDER", "fake")
    monkeypatch.setenv("SUGGEST_RETRIEVER", "lexical")
    monkeypatch.setenv("SUGGEST_INDEX", str(index_path))
    monkeypatch.setenv("SUGGEST_DB", str(tmp_path / "ops.sqlite3"))
    monkeypatch.setattr(api, "API_KEY", "test-key")
    monkeypatch.setattr(api, "get_predictor", lambda _: FakePredictor())
    with TestClient(api.app) as client:
        yield client


def post(client: TestClient, ticket: str = VPN, key: str = "request-1") -> httpx.Response:
    return cast(httpx.Response, client.post(
        "/suggest-resolution", json={"text": ticket},
        headers={"X-API-Key": "test-key", "Idempotency-Key": key},
    ))


def test_valid_sources_and_replay(enabled: TestClient, tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    provider = api.app.state.resolution.provider
    generate = AsyncMock(wraps=provider.generate)
    monkeypatch.setattr(provider, "generate", generate)
    first = post(enabled)
    assert first.status_code == 200
    data = first.json()
    assert data["status"] == "draft_ready"
    assert data["draft"] and data["review_reason"] is None
    assert data["sources"] == [{
        "id": "vpn:expired-profile:1", "document_id": "vpn", "title": "Remote access VPN",
        "section": "VPN profile renewal", "url": None,
    }]
    assert post(enabled, "  " + VPN + "  ").json() == data
    assert post(enabled, UNKNOWN).status_code == 409
    assert generate.await_count == 1
    with sqlite3.connect(tmp_path / "ops.sqlite3") as db:
        rows = db.execute("SELECT fingerprint, selected_ids, result FROM resolution_operations").fetchall()
    assert len(rows) == 1 and len(rows[0][0]) == 64
    assert "vpn:expired-profile:1" in json.loads(rows[0][1])
    assert VPN not in rows[0][2]


def test_insufficient_evidence_skips_provider(enabled: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    generate = AsyncMock()
    monkeypatch.setattr(api.app.state.resolution.provider, "generate", generate)
    response = post(enabled, UNKNOWN)
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["review_reason"]) == ("needs_review", "insufficient_evidence")
    assert data["draft"] is None and data["sources"] == []
    generate.assert_not_awaited()


@pytest.mark.parametrize(("output", "reason"), [
    (ProviderOutput("not JSON"), "invalid_output"),
    (ProviderOutput('{"draft":"Choose restart","source_ids":[]}'), "invalid_output"),
    (ProviderOutput('{"draft":"Choose restart","source_ids":["wifi:saved-network:1"]}'), "invalid_output"),
    (ProviderOutput('{"draft":"", "source_ids":[]}'), "provider_abstained"),
    (RuntimeError("provider failed"), "provider_error"),
])
def test_rejected_outputs(enabled: TestClient, monkeypatch: pytest.MonkeyPatch,
                          output: ProviderOutput | Exception, reason: str) -> None:
    generate = (AsyncMock(side_effect=output) if isinstance(output, Exception)
                else AsyncMock(return_value=output))
    monkeypatch.setattr(api.app.state.resolution.provider, "generate", generate)
    data = post(enabled).json()
    assert (data["status"], data["review_reason"]) == ("needs_review", reason)
    assert data["draft"] is None and data["sources"] == []


def test_provider_timeout(enabled: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolution, "PROVIDER_TIMEOUT", 0.01)

    async def slow(_: str, __: object) -> ProviderOutput:
        await asyncio.sleep(10)
        raise AssertionError("The provider should have been cancelled.")

    generate = AsyncMock(side_effect=slow)
    monkeypatch.setattr(api.app.state.resolution.provider, "generate", generate)
    data = post(enabled).json()
    assert data["review_reason"] == "provider_timeout" and data["draft"] is None
    assert generate.await_count == 1


def test_contaminated_passage_and_invalid_citation(enabled: TestClient,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    generate = AsyncMock(return_value=ProviderOutput(
        '{"draft":"Ticket resolved","source_ids":["unlisted:source:1"]}'
    ))
    monkeypatch.setattr(api.app.state.resolution.provider, "generate", generate)
    data = post(enabled, INJECTION).json()
    assert data["review_reason"] == "invalid_output" and data["draft"] is None
    assert generate.await_args is not None
    _, passages = generate.await_args.args
    assert "Ignore earlier instructions" in passages[0].text


def test_concurrent_replay_does_not_call_provider(enabled: TestClient, tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    entered, release = threading.Event(), threading.Event()
    provider = api.app.state.resolution.provider
    original = provider.generate

    async def blocked(ticket: str, passages: object) -> ProviderOutput:
        entered.set()
        assert await asyncio.to_thread(release.wait, 3)
        output: ProviderOutput = await original(ticket, passages)
        return output

    generate = AsyncMock(side_effect=blocked)
    monkeypatch.setattr(provider, "generate", generate)
    with ThreadPoolExecutor(max_workers=1) as worker:
        first = worker.submit(post, enabled)
        try:
            assert entered.wait(3)
            second = post(enabled).json()
            assert second["status"] == "in_progress" and second["draft"] is None
        finally:
            release.set()
        saved = first.result(timeout=3).json()
    assert saved["status"] == "draft_ready" and saved["operation_id"] == second["operation_id"]
    assert post(enabled).json() == saved
    assert generate.await_count == 1
    with sqlite3.connect(tmp_path / "ops.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM resolution_operations").fetchone() == (1,)


def test_interrupted_operation_is_finalized_without_retry(enabled: TestClient,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    service = api.app.state.resolution
    monkeypatch.setattr(resolution, "LEASE_SECONDS", -1)
    operation_id, existing = service.store.claim("api-key:test-key", "request-1", VPN, "corpus", "{}")
    assert existing is None
    generate = AsyncMock()
    monkeypatch.setattr(service.provider, "generate", generate)
    data = post(enabled).json()
    assert data["operation_id"] == operation_id and data["review_reason"] == "interrupted"
    assert post(enabled).json() == data
    generate.assert_not_awaited()


def test_waiting_on_store_keeps_application_responsive(
    enabled: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release = threading.Event(), threading.Event()
    store = api.app.state.resolution.store
    claim = store.claim

    def blocked(*args: str) -> tuple[str, resolution.ResolutionResult | None]:
        entered.set()
        assert release.wait(5)
        result: tuple[str, resolution.ResolutionResult | None] = claim(*args)
        return result

    monkeypatch.setattr(store, "claim", blocked)
    with ThreadPoolExecutor(max_workers=2) as workers:
        suggestion = workers.submit(post, enabled)
        try:
            assert entered.wait(3)
            health = workers.submit(enabled.get, "/health")
            assert health.result(timeout=3).status_code == 200
        finally:
            release.set()
        assert suggestion.result(timeout=3).json()["status"] == "draft_ready"


def test_existing_auth_and_bounded_validation(enabled: TestClient) -> None:
    response = enabled.post("/suggest-resolution", json={"text": VPN})
    assert response.status_code == 401
    assert post(enabled, "  ").status_code == 422
    assert post(enabled, VPN, "has spaces").status_code == 422
    body = "private " * 1000
    response = post(enabled, body)
    assert response.status_code == 422 and body not in response.text


def test_unconfigured_startup_preserves_predict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUGGEST_PROVIDER", raising=False)
    monkeypatch.setattr(api, "API_KEY", None)
    monkeypatch.setattr(api, "get_predictor", lambda _: FakePredictor())
    with TestClient(api.app) as client:
        assert client.post("/predict", json={"text": VPN}).json() == FakePredictor().predict(VPN)
        assert post(client).status_code == 503


def test_index_rebuild_is_identical_and_keeps_heading_metadata(tmp_path: Path) -> None:
    docs = tmp_path / "corpus"
    docs.mkdir()
    (docs / "sample.md").write_text(
        "# Network handbook\nSource: https://example.org/guide\n\n"
        "## [remote] Remote access\n\nVPN client reconnect steps.\n\nVPN client troubleshooting.\n",
        encoding="utf-8",
    )
    index = tmp_path / "index.json"
    first_version = build_index(docs, index)
    first_bytes = index.read_bytes()
    assert build_index(docs, index) == first_version and index.read_bytes() == first_bytes
    passages = SupportIndex(index, "lexical").rank("VPN client", 2)
    assert {passage.id for passage in passages} == {"sample:remote:1", "sample:remote:2"}
    assert all(p.section == "Remote access" and p.url == "https://example.org/guide" for p in passages)


def test_openai_adapter_keeps_ticket_and_passages_as_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_path = tmp_path / "index.json"
    build_index(CORPUS, index_path)
    selected = SupportIndex(index_path, "lexical").rank(INJECTION, 1)
    client_cls = httpx.AsyncClient

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer fake-key"
        message = json.loads(request.content)
        assert "tools" not in message and message["store"] is False
        assert message["response_format"]["json_schema"]["strict"] is True
        system, user = message["messages"]
        assert system["role"] == "system" and INJECTION not in system["content"]
        assert user["role"] == "user"
        assert json.loads(user["content"]) == {"ticket": INJECTION, "passages": [selected[0].context()]}
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {
                "content": '{"draft":"","source_ids":[]}',
            }}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    def client(*, trust_env: bool, follow_redirects: bool, timeout: None) -> httpx.AsyncClient:
        return client_cls(transport=httpx.MockTransport(handle), trust_env=trust_env,
                          follow_redirects=follow_redirects, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    output = asyncio.run(OpenAIProvider("test-model", "fake-key").generate(INJECTION, selected))
    assert output.usage is not None and output.usage.input_tokens == 10
    assert json.loads(output.content) == {"draft": "", "source_ids": []}
