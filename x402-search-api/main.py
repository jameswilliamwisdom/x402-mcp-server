"""
x402 Search API
Web search via Tavily — returns ranked results with title, URL, snippet, score.
Per-wallet daily rate limiting. Free test endpoint. Gated behind x402 USDC payment.
"""

import os
import json
import logging
import threading
from datetime import date
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

from tavily import AsyncTavilyClient
from tavily.errors import UsageLimitExceededError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# Logger and Constants
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x402-search")

DAILY_QUERY_LIMIT = 50
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixture.json")


# =============================================================================
# Per-Wallet Daily Rate Limiter
# =============================================================================

_wallet_counts: dict = {}   # {wallet_addr_lower: (count: int, day: date)}
_wallet_lock = threading.Lock()


def get_wallet_address(request: Request):
    """Extract payer wallet from fastapi-x402 decoded_payment state.

    Structure (from fastapi-x402 0.1.8 source inspection):
    request.state.decoded_payment = {
        "payload": {
            "authorization": {"from": "0xPayerWallet", ...},
            "signature": "0x..."
        }
    }
    """
    decoded = getattr(request.state, "decoded_payment", None)
    if decoded is None:
        return None
    try:
        return decoded["payload"]["authorization"]["from"].lower()
    except (KeyError, TypeError, AttributeError):
        return None


def check_and_increment_wallet_limit(wallet) -> None:
    """Check daily limit and increment counter atomically.
    Raises HTTP 429 if limit reached. No-op if wallet is None.
    """
    if wallet is None:
        return
    today = date.today()
    with _wallet_lock:
        count, recorded_day = _wallet_counts.get(wallet, (0, today))
        if recorded_day != today:
            count = 0  # New day -- reset
        if count >= DAILY_QUERY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "daily_limit_exceeded",
                    "limit": DAILY_QUERY_LIMIT,
                    "resets": "midnight UTC",
                }
            )
        _wallet_counts[wallet] = (count + 1, today)


# =============================================================================
# Tavily Search Function
# =============================================================================

async def run_search(
    query: str,
    max_results: int = 5,
    include_answer: bool = False,
    include_domains: list = None,
    exclude_domains: list = None,
) -> dict:
    """Call Tavily and return shaped response with 'snippet' field."""
    raw = await tavily_client.search(
        query=query,
        search_depth="basic",               # Always basic: 1 credit = $0.008
        max_results=max_results,
        include_answer=include_answer,       # bool only: True or False
        include_domains=include_domains or [],
        exclude_domains=exclude_domains or [],
    )

    shaped_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),    # Rename content -> snippet
            "score": round(float(r.get("score", 0.0)), 4),
        }
        for r in raw.get("results", [])
    ]

    response = {
        "query": query,
        "results": shaped_results,
    }

    if include_answer:
        response["answer"] = raw.get("answer") or None

    return response


# =============================================================================
# Lifespan — Initialize AsyncTavilyClient
# =============================================================================

tavily_client: AsyncTavilyClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tavily_client
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — search endpoint will fail")
    tavily_client = AsyncTavilyClient(api_key=api_key)
    yield
    # No cleanup needed — AsyncTavilyClient creates new httpx session per call


# =============================================================================
# FastAPI App Setup
# =============================================================================

app = FastAPI(
    title="Bismuth Search",
    description="Web search via Tavily with ranked results, snippets, and optional AI-synthesized answer. Part of the Bismuth utility API suite for AI agents.",
    version="2.0.0",
    lifespan=lifespan,
    contact={
        "name": "Bismuth",
        "url": "https://usebismuth.com",
        "email": os.getenv("CONTACT_EMAIL", "james@usebismuth.com"),
    },
)

PAY_TO = os.getenv("PAY_TO_ADDRESS")
if not PAY_TO:
    raise RuntimeError("PAY_TO_ADDRESS env var required (Base network wallet)")

BASE_NETWORK: Network = "eip155:8453"
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.daydreams.systems")

_facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
_x402_server = x402ResourceServer(_facilitator)
_x402_server.register(BASE_NETWORK, ExactEvmServerScheme())

_paid_routes = {
    "POST /search": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.01", network=BASE_NETWORK)],
        mime_type="application/json",
        description="Web search via Tavily",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, routes=_paid_routes, server=_x402_server)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# No SSRFMiddleware — there are no user-supplied URLs to validate.
# The only outbound call is to api.tavily.com, a trusted third-party.


# =============================================================================
# Rate Limiter Setup (slowapi — for free test endpoint)
# =============================================================================

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


# =============================================================================
# Pydantic Request Model
# =============================================================================

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=400,
                       description="Search query string")
    max_results: int = Field(5, ge=1, le=10,
                              description="Number of results to return (1-10)")
    include_answer: bool = Field(False,
                                  description="Include a synthesized answer above results")
    include_domains: Optional[List[str]] = Field(None, max_length=20,
                                                  description="Restrict results to these domains")
    exclude_domains: Optional[List[str]] = Field(None, max_length=20,
                                                  description="Exclude these domains from results")


# =============================================================================
# Route Handlers
# =============================================================================

# =============================================================================
# OpenAPI x402 v2 Extensions + Favicon
# =============================================================================

_original_openapi_fn = app.openapi


def _openapi_with_x402_v2():
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi_fn()
    schema["info"]["x-guidance"] = (
        "Bismuth Search — Web search via Tavily for AI agents. "
        "POST /search with {query, max_results?, include_answer?, include_domains?, exclude_domains?} "
        "returns ranked results with title/URL/snippet/score ($0.01 USDC on Base). "
        "Free fixture at GET /search/test."
    )
    for (path, method), amount in [(("/search", "post"), "0.010000")]:
        op = schema.get("paths", {}).get(path, {}).get(method)
        if op is None:
            continue
        op["x-payment-info"] = {
            "price": {"mode": "fixed", "currency": "USD", "amount": amount},
            "protocols": [{"x402": {}}],
        }
        op.setdefault("responses", {})["402"] = {"description": "Payment Required"}
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_x402_v2

_FAVICON_PATH = os.path.join(os.path.dirname(__file__), "favicon.ico")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if os.path.exists(_FAVICON_PATH):
        return FileResponse(_FAVICON_PATH, media_type="image/x-icon")
    raise HTTPException(status_code=404)


@app.api_route("/.well-known/x402", methods=["GET", "HEAD"])
async def well_known_x402():
    """x402 discovery — indexed by x402scan and other ecosystem crawlers."""
    return {
        "version": 1,
        "x402Version": 2,
        "name": "Bismuth Search",
        "description": "Web search via Tavily with ranked results, snippets, and optional AI-synthesized answer. Part of the Bismuth utility API suite for AI agents.",
        "apiVersion": "1.0.0",
        "network": "base",
        "resource": {
            "url": "https://x402-search-api-production.up.railway.app",
            "description": "Bismuth Search — x402 USDC micropayments on Base",
            "mimeType": "application/json",
        },
        "services": [
            {
                "name": "Web Search",
                "endpoint": "/search",
                "method": "POST",
                "price": "$0.01",
                "description": "Search the web and receive ranked results with title, URL, snippet, and relevance score",
            },
        ],
        "resources": ["POST /search"],
        "documentation": "https://x402-search-api-production.up.railway.app/docs",
        "provider": {
            "name": "Bismuth",
            "url": "https://usebismuth.com",
        },
    }


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "service": "x402-search-api",
        "price": "$0.01",
        "test": "/search/test",
        "description": "Web search via Tavily — returns ranked results with title, URL, snippet, score",
        "endpoints": {
            "POST /search": "Search the web (requires x402 USDC payment: $0.01)",
            "GET /search/test": "Free fixture response",
            "GET /health": "Health check",
        },
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {
        "status": "healthy",
        "tavily": "configured" if tavily_client else "not configured",
    }


@app.api_route("/search/test", methods=["GET", "HEAD"])
@limiter.limit("100/hour")
async def search_test(request: Request):
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@app.post("/search")
async def search(request: Request, body: SearchRequest):
    # Per-wallet rate limit — call AFTER @pay has verified payment
    # and set request.state.decoded_payment
    wallet = get_wallet_address(request)
    check_and_increment_wallet_limit(wallet)

    try:
        result = await run_search(
            query=body.query,
            max_results=body.max_results,
            include_answer=body.include_answer,
            include_domains=body.include_domains,
            exclude_domains=body.exclude_domains,
        )
    except UsageLimitExceededError:
        raise HTTPException(
            status_code=503,
            detail="Tavily API credit limit reached. Contact service operator.",
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    return result
