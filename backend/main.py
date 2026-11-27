import logging
import os
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .api.v1.catalog import router as catalog_router
from .api.v1.analytics import router as analytics_router
from .api.v1.customers import router as customers_router
from .api.v1.orders import router as orders_router
from .database import check_database_connection
from .schemas.analytics import DatabaseHealthResponse, HealthResponse
from .schemas.common import ErrorResponse


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Olist E-commerce Analytics API",
    version="1.0.0",
    description="Read-only catalog and analytics API for the Olist e-commerce dataset.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "Accept"],
)
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
) -> JSONResponse:
    """Return the shared error response shape used by every handler."""
    payload = ErrorResponse(
        error={"code": code, "message": message, "field": field}
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert FastAPI HTTP errors into the documented error format."""
    del request
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code_by_status = {404: "NOT_FOUND", 422: "VALIDATION_ERROR", 503: "DATABASE_UNAVAILABLE"}
    return _error_response(exc.status_code, code_by_status.get(exc.status_code, "HTTP_ERROR"), message)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a concise 422 response without exposing internal stack details."""
    del request
    first_error = exc.errors()[0] if exc.errors() else {}
    location = first_error.get("loc", ())
    field = str(location[-1]) if location else None
    return _error_response(422, "VALIDATION_ERROR", "Request validation failed", field)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Hide database details from clients while recording the server-side error."""
    del request
    logger.exception("Database operation failed", exc_info=exc)
    return _error_response(503, "DATABASE_UNAVAILABLE", "Database unavailable")


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe generic response for unexpected server errors."""
    del request
    logger.exception("Unhandled application error", exc_info=exc)
    return _error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected server error occurred")


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add basic browser security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/")
def root():
    return {"message": "Hello from FastAPI"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return application health after checking database connectivity."""
    try:
        check_database_connection()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return HealthResponse(status="ok", service=app.title, version=app.version)


@app.get("/health/database", response_model=DatabaseHealthResponse)
def database_health() -> DatabaseHealthResponse:
    """Check the database and return the elapsed query time."""
    started = perf_counter()
    try:
        check_database_connection()
    except Exception as exc:
        latency_ms = (perf_counter() - started) * 1000
        return DatabaseHealthResponse(
            status="unavailable",
            database="ecommerce",
            latency_ms=latency_ms,
        )
    return DatabaseHealthResponse(
        status="ok",
        database="ecommerce",
        latency_ms=(perf_counter() - started) * 1000,
    )
