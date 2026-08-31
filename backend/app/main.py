"""Groww Mutual Fund FAQ Assistant — FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

app = FastAPI(
    title="Groww Mutual Fund FAQ Assistant",
    description="Facts-only mutual fund information. No investment advice.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "Groww Mutual Fund FAQ Assistant", "docs": "/docs"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Sorry, I couldn't process that right now."})


@app.on_event("startup")
def startup_note():
    logger.info("Starting Groww Mutual Fund FAQ Assistant (facts-only)")
    if not settings.supabase_key:
        logger.warning("SUPABASE_KEY is not set - retrieval endpoints will fail until configured")
