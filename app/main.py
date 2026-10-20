
import logging
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import database
from .config import settings
from .limiter import limiter
from .routers import auth, posts, upload, users, websocket
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.requests")

app = FastAPI(
    title="Blog API",
    description="FastAPI + PostgreSQL + JWT + Alembic + CORS",
    version="1.0.0",
    debug=settings.debug and not settings.is_production,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.mount(
    "/uploads",
    StaticFiles(directory=upload.UPLOAD_DIR),
    name="uploads",
)

# Asosiy API routerlari
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(websocket.router)
# API v1 manzillari
app.include_router(posts.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed: %s %s",
            request.method,
            request.url.path,
        )
        raise

    duration_ms = (perf_counter() - started_at) * 1000

    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Blog API",
        "version": app.version,
        "environment": settings.environment,
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(database.get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Health check database probe failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
        "environment": settings.environment,
        "version": app.version,
    }
