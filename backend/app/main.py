from contextlib import asynccontextmanager
from contextlib import suppress
import asyncio
import re
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pymongo.errors import PyMongoError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.observability import configure_logging, logger, operations
from app.core.security import initialize_firebase
from app.database.mongodb import DatabaseUnavailableError, connect_mongodb, disconnect_mongodb, mongodb_status
from app.services.job_control_service import recover_interrupted_jobs

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_firebase(settings)
    connected = await connect_mongodb(settings)
    if connected:
        try:
            await recover_interrupted_jobs()
        except (PyMongoError, OSError, TimeoutError) as exc:
            logger.warning("mongodb_job_recovery_deferred", error_type=type(exc).__name__)
    else:
        logger.warning("mongodb_unavailable_starting_degraded", retry_seconds=settings.mongodb_retry_seconds)

    async def reconnect() -> None:
        while True:
            await asyncio.sleep(settings.mongodb_retry_seconds)
            previous = mongodb_status()
            if previous["connected"] and previous["indexes_ready"]:
                continue
            if await connect_mongodb(settings):
                current = mongodb_status()
                if not previous["connected"]:
                    logger.info("mongodb_reconnected")
                    try:
                        await recover_interrupted_jobs()
                    except (PyMongoError, OSError, TimeoutError) as exc:
                        logger.warning("mongodb_job_recovery_deferred", error_type=type(exc).__name__)
                elif not previous["indexes_ready"] and current["indexes_ready"]:
                    logger.info("mongodb_indexes_ready")

    reconnect_task = asyncio.create_task(reconnect(), name="mongodb-reconnect")
    try:
        yield
    finally:
        reconnect_task.cancel()
        with suppress(asyncio.CancelledError):
            await reconnect_task
        await disconnect_mongodb()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")[:128]
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied_id) else str(uuid4())
    started = monotonic()
    operations.begin()
    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "unmatched")
        duration_ms = round((monotonic() - started) * 1000)
        operations.finish(request.method, route, status_code, duration_ms)
        logger.info("request_completed", request_id=request_id, method=request.method, route=route, status_code=status_code, duration_ms=duration_ms)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [{key: item[key] for key in ("type", "loc", "msg") if key in item} for item in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "The request contains invalid data", "details": details}})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_error(_: Request, __: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": {"code": "rate_limit_exceeded", "message": "Too many requests. Please try again shortly."}})


@app.exception_handler(DatabaseUnavailableError)
async def database_unavailable(_: Request, __: DatabaseUnavailableError):
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": str(settings.mongodb_retry_seconds)},
        content={"error": {"code": "database_unavailable", "message": "Database connection is temporarily unavailable. MultiSource AI is retrying automatically."}},
    )


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception):
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "The service could not complete this request"}})


app.include_router(api_router, prefix=settings.api_v1_prefix)
