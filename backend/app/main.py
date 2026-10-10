"""Groww Mutual Fund FAQ Assistant — FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.routes import router
from .config import settings
from .safety import messages as M
from .utils.ratelimit import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# 1. Modern lifespan handler replaces deprecated @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
  logger.info("Starting Groww Mutual Fund FAQ Assistant (facts-only)")
  if not settings.supabase_key:
    logger.warning(
        "SUPABASE_KEY is not set - retrieval endpoints will fail until"
        " configured"
    )
  yield
  logger.info("Shutting down Groww Mutual Fund FAQ Assistant")


app = FastAPI(
    title="Groww Mutual Fund FAQ Assistant",
    description="Facts-only mutual fund information. No investment advice.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 2. Clean CORS origin parsing
_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# 3. Health & Uptime checks
@app.get("/ping")
async def ping_get():
  return {"status": "ok"}


@app.head("/ping")
async def ping_head():
  # Return 200 with an empty body for HEAD requests
  return Response(status_code=200)


@app.get("/")
def root():
  return {"app": "Groww Mutual Fund FAQ Assistant", "docs": "/docs"}


# 4. Global exception fallback
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
  logger.exception("Unhandled error on %s", request.url.path)
  return JSONResponse(
      status_code=500, content={"detail": "Sorry, I couldn't process that right now."}
  )
