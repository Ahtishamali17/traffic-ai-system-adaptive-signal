"""
app/main.py
--------------------------------------------------------------------
Application entrypoint.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

This file is intentionally thin: it wires together config, logging,
database lifecycle, middleware, and routers. Real logic lives in
app/api (routes), app/services (business logic), app/tracking
(DeepSORT), app/analytics (reports/stats).
--------------------------------------------------------------------
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import ensure_storage_dirs, get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.logging import configure_logging, logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown hooks (modern FastAPI lifespan pattern,
    replaces the deprecated @app.on_event decorators).
    """
    # --- Startup ---
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} "
                f"[{settings.ENVIRONMENT}]")
    ensure_storage_dirs()
    await connect_to_mongo()
    logger.info("Startup complete. Ready to accept requests.")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    await close_mongo_connection()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-time AI-powered vehicle detection, tracking, and traffic analytics platform.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Lightweight request/response logging middleware."""
    logger.debug(f"--> {request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"<-- {request.method} {request.url.path} {response.status_code}")
    return response


# ---------------------------------------------------------------------
# Global exception handler (never leak stack traces to clients)
# ---------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error"},
    )


# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple liveness/readiness probe for Docker/K8s and uptime monitors."""
    return {
        "success": True,
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ---------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------
from app.api import analytics, detection, reports  # noqa: E402

app.include_router(detection.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
