import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import ApiError
from app.routers import (
    analyze,
    auth,
    collections,
    downloads,
    health,
    library,
    media,
    recommendations,
)
from app.services.downloader import sweep_stale_jobs
from app.services.storage import get_storage

settings = get_settings()
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_storage().root.mkdir(parents=True, exist_ok=True)
    # In-process jobs cannot survive a restart; surface them instead of
    # leaving rows stuck in an active state forever.
    await sweep_stale_jobs()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Universal Video Hub API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Any):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin not in settings.origins:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "forbidden",
                            "message": "Origin tidak diizinkan.",
                            "details": {},
                        }
                    },
                    headers={"x-request-id": request_id},
                )
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.payload(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Input tidak valid.",
                    "details": {"errors": jsonable_encoder(exc.errors())},
                }
            },
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(analyze.router, prefix="/api/v1")
    app.include_router(media.router, prefix="/api/v1")
    app.include_router(downloads.router, prefix="/api/v1")
    app.include_router(library.router, prefix="/api/v1")
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(recommendations.router, prefix="/api/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "uvh-api", "version": "0.1.0", "docs": "/api/docs"}

    return app


app = create_app()
