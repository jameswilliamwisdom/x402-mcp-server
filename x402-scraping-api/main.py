"""
x402 Scraping API
Scrape any URL and return structured JSON — markdown text, links, tables, images, and metadata.
Playwright-powered for JS-rendered pages. SSRF-protected. Gated behind x402 USDC payment.
"""

import os
import json
import socket
import ipaddress
import asyncio
import time
import logging
from io import StringIO
from typing import Optional, Annotated
from contextlib import asynccontextmanager
from collections import deque
import fnmatch
import posixpath
from urllib.parse import urlparse, urljoin, urlunsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_core import Url
from pydantic import UrlConstraints
from starlette.middleware.base import BaseHTTPMiddleware

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

from playwright.async_api import async_playwright, Browser

import trafilatura
from bs4 import BeautifulSoup
import pandas as pd
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# Logger and Constants
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x402-scraping")

TOTAL_BUDGET_S = 8.0
MAX_RESPONSE_BYTES = 5_000_000
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "websocket"}

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixture.json")
CRAWL_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "crawl_fixture.json")
CRAWL_PAGE_BUDGET_S = 6.0
CRAWL_TOTAL_BUDGET_S = 90.0


# =============================================================================
# SSRF Validation
# =============================================================================

def _assert_ip_public(ip) -> None:
    """Raise ValueError if the IP is in a blocked (non-public) range."""
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.1) before checking
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        _assert_ip_public(ip.ipv4_mapped)
        return
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
        raise ValueError(f"URL resolves to blocked IP range: {ip}")


def validate_url_for_ssrf(url: str) -> None:
    """Raises ValueError if the URL targets a private/internal resource.

    Uses getaddrinfo (not gethostbyname) to catch both IPv4 and IPv6 records.
    Checks ALL resolved addresses — not just the first.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed; only http/https accepted")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("No hostname in URL")

    # Reject bare IP literals that are already private (before DNS resolution)
    try:
        direct_ip = ipaddress.ip_address(hostname)
        _assert_ip_public(direct_ip)
        return  # Valid public IP literal — no DNS needed
    except ValueError as e:
        # Either it's a private IP (re-raise) or not an IP literal (continue to DNS)
        if "blocked IP range" in str(e):
            raise
        # Not an IP literal — fall through to DNS resolution

    try:
        records = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed: {e}")

    if not records:
        raise ValueError("DNS resolution returned no addresses")

    for record in records:
        ip_str = record[4][0].split("%")[0]  # Strip IPv6 scope ID
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Could not parse resolved IP: {ip_str!r}")
        _assert_ip_public(ip)


# =============================================================================
# Playwright Route Handlers
# =============================================================================

BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "websocket"}


async def handle_route(route):
    """Block non-content resource types to save memory and reduce load time.

    Does NOT block 'script' — required for JS rendering (SCRAPE-02, SCRAPE-03).
    Registered on context (not page) to avoid memory leaks.
    """
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()


async def abort_private_navigation(route):
    """Abort document-level navigations to private IPs (redirect-chain SSRF protection).

    Pre-flight SSRF check validates the input URL only. This handler catches
    redirect chains that land on private IPs after payment has been accepted.
    Registered on context (not page) to avoid memory leaks.
    """
    if route.request.resource_type == "document":
        try:
            validate_url_for_ssrf(route.request.url)
        except ValueError:
            await route.abort("blockedbyclient")
            return
    await route.continue_()


# =============================================================================
# Browser Lifecycle
# =============================================================================

browser: Optional[Browser] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage browser lifecycle — one browser for the process lifetime."""
    global browser

    logger.info("Starting Playwright Chromium browser...")
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )

    def on_browser_disconnect():
        global browser
        browser = None
        logger.error(
            "Playwright browser disconnected — Railway ON_FAILURE policy will restart container"
        )

    browser.on("disconnected", on_browser_disconnect)
    logger.info("Browser ready")

    yield

    if browser and browser.is_connected():
        await browser.close()
    logger.info("Browser closed — shutdown complete")


# =============================================================================
# FastAPI App + Middleware
# =============================================================================

app = FastAPI(
    title="Bismuth Scraping",
    description="Playwright-powered web scraping with structured markdown, links, tables, and BFS site crawl. SSRF-protected. Part of the Bismuth utility API suite for AI agents.",
    version="2.0.0",
    lifespan=lifespan,
    contact={
        "name": "Bismuth",
        "url": "https://usebismuth.com",
        "email": os.getenv("CONTACT_EMAIL", "james@usebismuth.com"),
    },
)

# x402 v2 payment middleware — official x402-foundation SDK
PAY_TO = os.getenv("PAY_TO_ADDRESS")
if not PAY_TO:
    raise RuntimeError("PAY_TO_ADDRESS env var required (Base network wallet)")

BASE_NETWORK: Network = "eip155:8453"
# Daydreams supports x402 v2 exact on Base mainnet (eip155:8453), no auth.
# x402.org is testnet-only; CDP requires auth. Override with FACILITATOR_URL.
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.daydreams.systems")

_facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
_x402_server = x402ResourceServer(_facilitator)
_x402_server.register(BASE_NETWORK, ExactEvmServerScheme())

_paid_routes = {
    "POST /scrape": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.02", network=BASE_NETWORK)],
        mime_type="application/json",
        description="Scrape a URL and return structured JSON",
    ),
    "POST /crawl": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.10", network=BASE_NETWORK)],
        mime_type="application/json",
        description="Shallow BFS crawl up to 15 pages from a seed URL",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, routes=_paid_routes, server=_x402_server)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SSRFMiddleware(BaseHTTPMiddleware):
    """Pre-payment SSRF validation.

    Added AFTER init_x402() — LIFO ordering means this runs FIRST, before payment.
    SSRF-blocked requests return 400 with no charge to the caller.
    """

    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path in ("/scrape", "/crawl"):
            try:
                body_bytes = await request.body()
                # Empty body → let x402 middleware fire 402; malformed JSON → let Pydantic handle
                if not body_bytes:
                    return await call_next(request)
                body = json.loads(body_bytes)
                url = body.get("url", "")
                if url:
                    validate_url_for_ssrf(str(url))
            except ValueError as e:
                if isinstance(e, json.JSONDecodeError):
                    pass  # Malformed body → let Pydantic reject downstream
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"SSRF validation failed: {e}"},
                    )
            except Exception:
                pass
        return await call_next(request)


# SSRFMiddleware added SECOND — LIFO means it runs FIRST (before payment check)
app.add_middleware(SSRFMiddleware)


# =============================================================================
# Rate Limiting
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
# Request Models
# =============================================================================

BoundedHttpUrl = Annotated[
    Url,
    UrlConstraints(allowed_schemes=["http", "https"], max_length=2048),
]


class ScrapeRequest(BaseModel):
    url: BoundedHttpUrl = Field(
        ..., description="URL to scrape (must be http/https, max 2048 chars)"
    )
    wait_for: Optional[str] = Field(
        None,
        max_length=500,
        description="CSS selector to wait for before extracting — for SPAs (e.g. '.article-body')",
    )


class CrawlRequest(BaseModel):
    url: BoundedHttpUrl = Field(
        ..., description="Seed URL to begin crawling (http/https, max 2048 chars)"
    )
    max_pages: int = Field(default=10, ge=1, le=15)
    max_depth: int = Field(default=2, ge=1, le=5)
    include_paths: list[str] = Field(default_factory=list, max_length=20)
    exclude_paths: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("include_paths", "exclude_paths", mode="before")
    @classmethod
    def validate_patterns(cls, v):
        for pat in v:
            if len(pat) > 200:
                raise ValueError("Path filter pattern must be <= 200 characters")
        return v


# =============================================================================
# Crawl Helpers
# =============================================================================

def normalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase scheme+host, strip fragment,
    normalize path (collapse ./..), preserve query string."""
    p = urlparse(url)
    path = posixpath.normpath(p.path) if p.path else "/"
    if p.path.endswith("/") and not path.endswith("/"):
        path += "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def _passes_path_filter(path: str, include_paths: list[str], exclude_paths: list[str]) -> bool:
    """Check URL path against include/exclude glob patterns.
    posixpath.normpath prevents traversal bypass (e.g. /blog/../admin/config)."""
    normalized = posixpath.normpath(path)
    if include_paths:
        # Expand "/blog/*" to also match "/blog" (bare prefix without trailing content)
        expanded = []
        for pat in include_paths:
            expanded.append(pat)
            if pat.endswith("/*"):
                expanded.append(pat[:-2])
        if not any(fnmatch.fnmatch(normalized, ep) for ep in expanded):
            return False
    if exclude_paths:
        expanded_ex = []
        for pat in exclude_paths:
            expanded_ex.append(pat)
            if pat.endswith("/*"):
                expanded_ex.append(pat[:-2])
        if any(fnmatch.fnmatch(normalized, ep) for ep in expanded_ex):
            return False
    return True


async def run_bfs_crawl(
    seed_url: str,
    max_pages: int,
    max_depth: int,
    include_paths: list[str],
    exclude_paths: list[str],
) -> dict:
    """Breadth-first crawl using deque FIFO. Reuses scrape_page() + extract_content().
    Returns partial results on per-page failure (CRAWL-07). Aborts only on browser death."""
    results = []
    reasons_skipped: list[str] = []
    pages_skipped = 0
    top_level_warnings: list[str] = []

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    norm_seed = normalize_url(seed_url)
    queue.append((seed_url, 0))
    visited.add(norm_seed)

    seed_netloc: str | None = None  # Derived from first page's final_url (Pitfall 4)
    crawl_start = time.monotonic()

    while queue and len(results) < max_pages:
        if time.monotonic() - crawl_start > CRAWL_TOTAL_BUDGET_S:
            top_level_warnings.append("crawl_timeout")
            break

        url, depth = queue.popleft()

        try:
            page_data = await scrape_page(url, wait_for=None)
        except HTTPException as e:
            if e.status_code == 503:
                # Browser dead — abort with partial results
                top_level_warnings.append("browser_unavailable")
                break
            results.append({
                "success": False, "url": url, "depth": depth,
                "error": "http_error", "detail": str(e.detail), "warnings": [],
            })
            pages_skipped += 1
            reasons_skipped.append("http_error")
            continue
        except Exception as e:
            results.append({
                "success": False, "url": url, "depth": depth,
                "error": "scrape_error", "detail": str(e), "warnings": [],
            })
            pages_skipped += 1
            reasons_skipped.append("scrape_error")
            continue

        html = page_data["html"]
        final_url = page_data["final_url"]
        status_code = page_data["status_code"]
        response = page_data["response"]
        extra_warnings = page_data["extra_warnings"]

        # Derive seed_netloc from first page's final_url (handles redirect, Pitfall 4)
        if seed_netloc is None:
            seed_netloc = urlparse(final_url).netloc.lower()

        # Add final_url to visited (redirect loop protection)
        visited.add(normalize_url(final_url))

        extracted = extract_content(html, final_url)
        if response:
            headers = response.headers
            extracted["metadata"].update({
                "status_code": status_code,
                "content_type": headers.get("content-type"),
                "content_language": headers.get("content-language"),
                "x_robots_tag": headers.get("x-robots-tag"),
            })

        results.append({
            "success": True,
            "url": url,
            "final_url": final_url,
            "depth": depth,
            **extracted,
            "warnings": extracted["warnings"] + extra_warnings,
        })

        # Discover links for next BFS level
        if depth < max_depth:
            for link in extracted["links"]:
                href = link["url"]
                resolved = urljoin(final_url, href)
                norm = normalize_url(resolved)

                parsed = urlparse(resolved)
                if parsed.scheme not in ("http", "https"):
                    continue
                if norm in visited:
                    continue

                # SSRF gate — every discovered URL (CRAWL-04, Pitfall 1)
                try:
                    validate_url_for_ssrf(resolved)
                except ValueError:
                    pages_skipped += 1
                    reasons_skipped.append("ssrf_blocked")
                    visited.add(norm)
                    continue

                # Same-origin gate (strict netloc match)
                if parsed.netloc.lower() != seed_netloc:
                    pages_skipped += 1
                    reasons_skipped.append("off_domain")
                    visited.add(norm)
                    continue

                # Path filter gate (CRAWL-05)
                if not _passes_path_filter(parsed.path, include_paths, exclude_paths):
                    pages_skipped += 1
                    reasons_skipped.append("path_filter")
                    visited.add(norm)
                    continue

                visited.add(norm)
                queue.append((resolved, depth + 1))

    succeeded = [r for r in results if r.get("success")]
    response_body = {
        "success": len(succeeded) > 0,
        "seed_url": seed_url,
        "pages_requested": len(results),
        "pages_crawled": len(succeeded),
        "pages_skipped": pages_skipped,
        "reasons_skipped": list(set(reasons_skipped)),
        "results": results,
    }
    if top_level_warnings:
        response_body["warnings"] = top_level_warnings
    return response_body


# =============================================================================
# Content Detection and Extraction
# =============================================================================

def detect_block(response, html: str) -> Optional[str]:
    """Return error code if the page appears to be blocked, None otherwise.

    Checks HTTP status codes that typically indicate blocks, plus Cloudflare
    challenge markers in the HTML body.
    """
    status = response.status if response else None
    if status in (403, 429, 503):
        return "blocked_by_protection"
    # Check first 2000 chars for Cloudflare / WAF challenge markers
    head = html[:2000]
    if (
        "Just a moment" in head
        or "cf-browser-verification" in head
        or "Access denied" in html[:500]
    ):
        return "blocked_by_protection"
    return None


def extract_content(html: str, page_url: str) -> dict:
    """Full extraction pipeline: markdown, links, images, tables, metadata.

    Uses trafilatura for main content + metadata, BeautifulSoup for links/images,
    and pandas for tables (handles rowspan/colspan correctly).
    """
    warnings = []

    # --- 1. Main content → markdown (trafilatura) ---
    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=False,    # Experimental in trafilatura — use BS4 instead
        include_tables=False,   # Tables handled by pandas below
        url=page_url,
        no_fallback=False,
    )

    if markdown is None:
        warnings.append("no_content_extracted")
    elif len(markdown.encode("utf-8")) > MAX_RESPONSE_BYTES:
        # Truncate by bytes (not characters) — correct for multi-byte Unicode
        encoded = markdown.encode("utf-8")
        markdown = encoded[:MAX_RESPONSE_BYTES].decode("utf-8", errors="ignore")
        warnings.append("truncated")

    # --- 2. Metadata (trafilatura) ---
    meta = trafilatura.extract_metadata(html, default_url=page_url)
    metadata = {
        "title": meta.title if meta else None,
        "description": meta.description if meta else None,
        "og_title": meta.og_title if meta and hasattr(meta, "og_title") else None,
        "og_image": meta.image if meta else None,
        "canonical_url": meta.url if meta else None,
        "language": meta.language if meta else None,
        # status_code, content_type, content_language, x_robots_tag added by caller
    }

    # --- 3. Links — BeautifulSoup on raw HTML ---
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        links.append({"url": urljoin(page_url, href), "text": tag.get_text(strip=True)})

    # --- 4. Images — BeautifulSoup on raw HTML ---
    images = []
    for tag in soup.find_all("img", src=True):
        images.append({
            "src": urljoin(page_url, tag.get("src", "")),
            "alt": tag.get("alt", ""),
        })

    # --- 5. Tables — pandas (handles rowspan/colspan correctly) ---
    tables = []
    try:
        dfs = pd.read_html(StringIO(html))
        for df in dfs:
            df.columns = [str(c) for c in df.columns]
            tables.append({
                "headers": list(df.columns),
                "rows": df.fillna("").values.tolist(),
            })
    except ValueError:
        pass  # No tables found — not an error

    return {
        "markdown": markdown,
        "links": links,
        "images": images,
        "tables": tables,
        "metadata": metadata,
        "warnings": warnings,
    }


# =============================================================================
# Core Scrape Function
# =============================================================================

async def scrape_page(url: str, wait_for: Optional[str]) -> dict:
    """Launch a browser context, navigate, wait if needed, extract HTML.

    Shared 8-second budget across goto() + wait_for_selector().
    Context is always closed in finally — browser is never closed here.
    """
    global browser

    if browser is None or not browser.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Browser unavailable — container is restarting. Try again in ~15 seconds.",
        )

    start = time.monotonic()

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        permissions=[],
        service_workers="block",
    )

    # Register route blocking BEFORE creating page (must be active before goto)
    await context.route("**/*", handle_route)
    # Register redirect-chain SSRF intercept on context (not page — avoids memory leak)
    await context.route("**/*", abort_private_navigation)

    try:
        page = await context.new_page()

        # Allocate remaining budget to page.goto()
        elapsed = time.monotonic() - start
        goto_timeout = max(1000, int((TOTAL_BUDGET_S - elapsed) * 1000))
        response = await page.goto(url, wait_until="domcontentloaded", timeout=goto_timeout)

        status_code = response.status if response else None

        # Allocate remaining budget to wait_for_selector()
        if wait_for:
            elapsed = time.monotonic() - start
            selector_timeout = max(500, int((TOTAL_BUDGET_S - elapsed) * 1000))
            await page.wait_for_selector(wait_for, timeout=selector_timeout)

        html = await page.content()
        final_url = page.url

        # Sanitize final_url — data: / blob: URLs are not useful to callers
        extra_warnings = []
        if final_url.startswith(("data:", "blob:")):
            final_url = url
            extra_warnings.append("navigation_to_non_http_url")

        return {
            "html": html,
            "final_url": final_url,
            "status_code": status_code,
            "response": response,
            "extra_warnings": extra_warnings,
        }

    finally:
        await context.close()  # Always close context; NEVER close browser


# =============================================================================
# Routes
# =============================================================================

def load_fixture() -> dict:
    """Load and return fixture.json content."""
    with open(FIXTURE_PATH, "r") as f:
        return json.load(f)


def load_crawl_fixture() -> dict:
    """Load and return crawl_fixture.json content."""
    with open(CRAWL_FIXTURE_PATH, "r") as f:
        return json.load(f)


# =============================================================================
# OpenAPI x402 v2 Extensions
# =============================================================================
# Injects info.x-guidance and per-operation x-payment-info + responses.402
# on paid endpoints. Consumed by x402scan and other discovery crawlers.

_original_openapi_fn = app.openapi


def _openapi_with_x402_v2():
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi_fn()

    schema["info"]["x-guidance"] = (
        "Bismuth Scraping — Playwright-powered web scraping and BFS site crawl for AI agents. "
        "POST /scrape with {url, wait_for?} returns structured markdown, links, tables, images, "
        "and metadata for a single URL ($0.02 USDC on Base). "
        "POST /crawl with {url, ...} shallow-crawls up to 15 pages from a seed URL ($0.10 USDC). "
        "Free fixtures at GET /scrape/test and GET /crawl/test. "
        "SSRF-protected: private/loopback/link-local IPs rejected before payment."
    )

    _paid_ops = {
        ("/scrape", "post"): "0.020000",
        ("/crawl", "post"): "0.100000",
    }
    for (path, method), amount in _paid_ops.items():
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


# =============================================================================
# Favicon
# =============================================================================

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
        "name": "Bismuth Scraping",
        "description": "Playwright-powered web scraping with structured markdown, links, tables, and BFS site crawl. SSRF-protected. Part of the Bismuth utility API suite for AI agents.",
        "apiVersion": "1.0.0",
        "network": "base",
        "resource": {
            "url": "https://x402-scraping-api-production.up.railway.app",
            "description": "Bismuth Scraping — x402 USDC micropayments on Base",
            "mimeType": "application/json",
        },
        "services": [
            {
                "name": "Scrape URL",
                "endpoint": "/scrape",
                "method": "POST",
                "price": "$0.02",
                "description": "Fetch a URL, execute JS, return structured markdown + links + tables + metadata",
            },
            {
                "name": "Crawl Site",
                "endpoint": "/crawl",
                "method": "POST",
                "price": "$0.10",
                "description": "BFS crawl up to 15 pages from a seed URL",
            },
        ],
        "resources": ["POST /scrape", "POST /crawl"],
        "documentation": "https://x402-scraping-api-production.up.railway.app/docs",
        "provider": {
            "name": "Bismuth",
            "url": "https://usebismuth.com",
        },
    }


@app.api_route("/", methods=["GET", "HEAD"])
async def info():
    """Service info and pricing."""
    return {
        "service": "x402-scraping-api",
        "price": "$0.02",
        "test": "/scrape/test",
        "description": "Scrape or crawl any URL and return structured JSON: markdown, links, tables, images, metadata",
        "endpoints": {
            "POST /scrape": "Scrape a URL (requires x402 USDC payment: $0.02)",
            "GET /scrape/test": "Free fixture response — demonstrates full response schema",
            "POST /crawl": "Shallow BFS crawl — up to 15 pages (requires x402 USDC payment: $0.10)",
            "GET /crawl/test": "Free crawl fixture response — demonstrates crawl response schema",
            "GET /health": "Health check (browser status)",
        },
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """Health check — always returns HTTP 200. Body includes browser status."""
    return {
        "status": "healthy",
        "browser": browser is not None and browser.is_connected(),
    }


@app.api_route("/scrape/test", methods=["GET", "HEAD"])
@limiter.limit("100/hour")
async def scrape_test(request: Request):
    """Free test endpoint — returns fixture data (no live scraping, no payment required).

    Rate limited at 100 requests/hour per IP.
    Use POST /scrape with x402 payment for live page scraping.
    """
    return load_fixture()


@app.post("/scrape")
async def scrape(request: Request, body: ScrapeRequest):
    """Scrape a URL and return structured JSON.

    Returns: markdown (main content, nav/ads stripped), links [{url, text}],
    tables [{headers, rows}], images [{src, alt}], metadata (title, description,
    og_title, og_image, canonical_url, language, status_code, content_type,
    content_language, x_robots_tag), final_url, warnings.

    Pricing: $0.02 USDC per scrape (Base network).
    SSRF protection: private/loopback IPs rejected before payment.
    """
    global browser

    if browser is None or not browser.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Browser unavailable — container is restarting. Try again in ~15 seconds.",
        )

    input_url = str(body.url)

    try:
        page_data = await scrape_page(input_url, body.wait_for)
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "timeout" in error_str.lower() or "TimeoutError" in type(e).__name__:
            return {
                "success": False,
                "url": input_url,
                "error": "timeout",
                "detail": f"Page load timed out after {TOTAL_BUDGET_S}s. Try with wait_for=None or a simpler URL.",
                "warnings": ["timeout"],
            }
        logger.error(f"Playwright error scraping {input_url}: {e}")
        return {
            "success": False,
            "url": input_url,
            "error": "browser_error",
            "detail": str(e),
            "warnings": [],
        }

    html = page_data["html"]
    final_url = page_data["final_url"]
    status_code = page_data["status_code"]
    response = page_data["response"]
    extra_warnings = page_data["extra_warnings"]

    # Extract response headers for metadata
    content_type = None
    content_language = None
    x_robots_tag = None
    if response:
        headers = response.headers
        content_type = headers.get("content-type")
        content_language = headers.get("content-language")
        x_robots_tag = headers.get("x-robots-tag")

    # Reject non-HTML content types (PDF, images, etc.)
    if content_type and not any(
        t in content_type.lower()
        for t in ("text/html", "application/xhtml", "text/xml", "application/xml")
    ):
        return {
            "success": False,
            "url": input_url,
            "final_url": final_url,
            "error": "non_html_content",
            "detail": f"Content-Type '{content_type}' is not HTML. Use other x402 APIs for non-HTML content.",
            "warnings": [],
        }

    # Check for Cloudflare / WAF blocks
    block_error = detect_block(response, html)
    if block_error:
        return {
            "success": False,
            "url": input_url,
            "final_url": final_url,
            "error": block_error,
            "detail": "Page is protected by a firewall or anti-bot system (Cloudflare, CAPTCHA, etc.).",
            "warnings": [],
        }

    # Extract content
    extracted = extract_content(html, final_url)
    warnings = extracted["warnings"] + extra_warnings

    # Merge HTTP headers into metadata
    extracted["metadata"]["status_code"] = status_code
    extracted["metadata"]["content_type"] = content_type
    extracted["metadata"]["content_language"] = content_language
    extracted["metadata"]["x_robots_tag"] = x_robots_tag

    return {
        "success": True,
        "url": input_url,
        "final_url": final_url,
        "markdown": extracted["markdown"],
        "links": extracted["links"],
        "tables": extracted["tables"],
        "images": extracted["images"],
        "metadata": extracted["metadata"],
        "warnings": warnings,
    }


# =============================================================================
# Crawl Routes
# =============================================================================

@app.api_route("/crawl/test", methods=["GET", "HEAD"])
@limiter.limit("100/hour")
async def crawl_test(request: Request):
    """Free test endpoint — returns fixture data (no live crawl, no payment required)."""
    return load_crawl_fixture()


@app.post("/crawl")
async def crawl(request: Request, body: CrawlRequest):
    """Shallow BFS crawl — up to 15 pages, returns per-page extraction results.

    Same extraction pipeline as POST /scrape. SSRF-validated on every discovered URL.
    Pricing: $0.10 USDC per crawl (Base network).
    """
    global browser

    if browser is None or not browser.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Browser unavailable — container is restarting. Try again in ~15 seconds.",
        )

    seed_url = str(body.url)

    try:
        return await run_bfs_crawl(
            seed_url=seed_url,
            max_pages=body.max_pages,
            max_depth=body.max_depth,
            include_paths=body.include_paths,
            exclude_paths=body.exclude_paths,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Crawl error for {seed_url}: {e}")
        return {
            "success": False,
            "seed_url": seed_url,
            "pages_requested": 0,
            "pages_crawled": 0,
            "pages_skipped": 0,
            "reasons_skipped": [],
            "results": [],
            "error": "crawl_error",
            "detail": str(e),
        }
