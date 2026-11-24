import json
import os
import secrets
import sqlite3
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.routing import Match

from app.resolution.service import (
    IdempotencyConflict,
    ResolutionResult,
    ResolutionService,
    service_from_env,
)
from app.schemas import PredictionResponse as PredictionResponse
from app.schemas import TicketRequest as TicketRequest
from app.schemas import TopPrediction as TopPrediction
from src.inference import PredictionResult, get_predictor
from src.paths import METRICS_DIR

APP_ENV = os.getenv("APP_ENV", "development").lower()
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "auto")

STATIC_DIR = Path(__file__).resolve().parent / "static"


# Fixed label for unmatched routes so arbitrary URLs cannot create unbounded cardinality.
_UNMATCHED_ROUTE = "UNMATCHED"

HTTP_REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)
PREDICTION_REQUESTS = Counter("prediction_requests_total", "Total prediction requests")
AUTO_ROUTE_COUNT = Counter("auto_route_total", "Total auto-routed predictions")
MANUAL_REVIEW_COUNT = Counter("manual_review_total", "Total predictions needing manual review")
PREDICTION_CONFIDENCE = Histogram("prediction_confidence", "Prediction confidence score")


def _resolve_route_template(request: Request) -> str:
    """Return the matched route template or a fixed sentinel for unmatched routes."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            path: str = getattr(route, "path", _UNMATCHED_ROUTE)
            return path
    return _UNMATCHED_ROUTE


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.getenv("API_KEY")
    if APP_ENV == "production" and not api_key:
        raise RuntimeError(
            "API_KEY must be set when APP_ENV=production. "
            "Set the variable or switch to APP_ENV=development for local/test use."
        )
    print(f"Loading model: {MODEL_BACKEND} (APP_ENV={APP_ENV})")
    app.state.predictor = get_predictor(MODEL_BACKEND)
    app.state.resolution = service_from_env(api_key_configured=bool(API_KEY))
    try:
        yield
    finally:
        app.state.predictor = None
        app.state.resolution = None


app = FastAPI(
    title="QueuePilot",
    description="Automatically classifies IT service tickets into support categories.",
    version="1.0.0",
    lifespan=lifespan,
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.middleware("http")
async def monitor_requests(request: Request, call_next: Any) -> Any:
    start_time = time.time()
    endpoint = _resolve_route_template(request)
    status_code = 500
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.time() - start_time
        if endpoint != "/metrics":
            HTTP_REQUESTS.labels(
                method=request.method, endpoint=endpoint, status=status_code
            ).inc()
            HTTP_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)


API_KEY = os.getenv("API_KEY")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # When API_KEY is unset and not in production, the service runs in open/demo mode.
    if API_KEY is None:
        return
    if x_api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, exc: RequestValidationError) -> Response:
    if getattr(request.scope.get("route"), "path", None) == "/suggest-resolution":
        # Keep ticket text and idempotency keys out of validation responses.
        exc = RequestValidationError([
            {key: value for key, value in error.items() if key in {"type", "loc", "msg"}}
            for error in exc.errors()
        ])
    return await request_validation_exception_handler(request, exc)


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Serve the ticket classification UI."""
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")



@app.get("/health")
def health() -> dict[str, object]:
    predictor = app.state.predictor
    return {
        "status": "ok",
        "model_backend": getattr(predictor, "backend", MODEL_BACKEND),
        "model_sha256": getattr(predictor, "model_sha256", None),
        "threshold": getattr(predictor, "threshold", None),
    }


@app.get("/model-info", include_in_schema=False)
def model_info() -> dict[str, object]:
    """Serve persisted evaluation metrics for the UI's model panel (read-only)."""
    predictor = app.state.predictor
    backend = getattr(predictor, "backend", None)
    model_hash = getattr(predictor, "model_sha256", None)
    info: dict[str, object] = {"available": False, "model_backend": backend,
                               "model_sha256": model_hash,
                               "partitions": {"routing": "test", "classification": "test",
                                              "calibration": "calibration_holdout"}}
    if backend not in {"baseline", "cnn"} or not model_hash:
        return info
    prefix = "baseline" if backend == "baseline" else "cnn"
    metric_files = {
        "routing": "baseline_routing_metrics.json" if backend == "baseline" else "routing_metrics.json",
        "classification": f"{prefix}_metrics.json",
        "calibration": f"{prefix}_calibration_holdout_metrics.json",
    }
    try:
        for key, filename in metric_files.items():
            with open(METRICS_DIR / filename, encoding="utf-8") as f:
                report = json.load(f)
            if not isinstance(report, dict) or report.get("model_sha256") != model_hash:
                return info
            info[key] = report
    except (OSError, ValueError):
        return {**info, "available": False}
    info["available"] = True
    return info



@app.post("/predict", response_model=PredictionResponse)
def predict_ticket(
    request: TicketRequest,
    _: None = Depends(require_api_key),
) -> PredictionResult:
    PREDICTION_REQUESTS.inc()
    result: PredictionResult = app.state.predictor.predict(request.text)

    PREDICTION_CONFIDENCE.observe(result["confidence"])

    if result["needs_manual_review"]:
        MANUAL_REVIEW_COUNT.inc()
    else:
        AUTO_ROUTE_COUNT.inc()

    return result


@app.post("/suggest-resolution", response_model=ResolutionResult)
async def suggest_resolution(
    request: Request,
    ticket: TicketRequest,
    idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"),
    _: None = Depends(require_api_key),
) -> ResolutionResult:
    service: ResolutionService | None = getattr(request.app.state, "resolution", None)
    if service is None:
        raise HTTPException(503, detail="Resolution suggestions are disabled.")
    scope = "anonymous" if API_KEY is None else f"api-key:{API_KEY}"
    try:
        return await service.suggest(ticket.text, scope, idempotency_key)
    except IdempotencyConflict:
        raise HTTPException(409, detail="Idempotency-Key already used for a different ticket.") from None
    except (sqlite3.Error, TimeoutError):
        raise HTTPException(503, detail="Resolution operation storage is unavailable.") from None
