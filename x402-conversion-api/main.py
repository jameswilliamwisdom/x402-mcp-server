"""
x402 Conversion API
Convert files via URL: image resize/reformat (Pillow), CSV-to-JSON (stdlib), HTML-to-PDF (WeasyPrint), DOCX-to-PDF (mammoth + WeasyPrint).
All operations gated behind x402 USDC micropayment. SSRF-protected streaming download pipeline.
"""

import os
import json
import socket
import ipaddress
import logging
import csv
import base64
import tempfile
from io import StringIO, BytesIO
from typing import Optional, Annotated, Literal, Union
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from pydantic_core import Url
from pydantic import UrlConstraints
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

from PIL import Image, UnidentifiedImageError
import weasyprint
from weasyprint.urls import default_url_fetcher
import httpx
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# Logger and Constants
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x402-conversion")

MAX_FILE_BYTES = 10 * 1024 * 1024      # 10MB input limit
MAX_OUTPUT_BYTES = 8 * 1024 * 1024     # 8MB output limit (before base64)
MAX_PIXELS = 50_000_000                # 50MP decompression bomb guard
ALLOWED_SCHEMES = {"http", "https"}
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixture.json")
MIME_TYPES = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


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
# Async File Download with Streaming Size Enforcement
# =============================================================================

async def download_file(url: str) -> bytes:
    """Download a file from url with streaming 10MB size enforcement and redirect SSRF re-validation.

    Two-layer size check: Content-Length header fast path + mandatory streaming accumulator
    (handles servers that omit Content-Length).
    """
    def on_redirect(response):
        location = response.headers.get("location", "")
        if location:
            validate_url_for_ssrf(location)  # Re-validate each redirect hop

    async with httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=5,
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
        event_hooks={"response": [on_redirect]},
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            # Fast path: reject if Content-Length header exceeds limit
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_FILE_BYTES:
                raise ValueError(
                    f"Source file is {int(content_length) / 1024 / 1024:.1f}MB"
                    f" — exceeds 10MB limit."
                )

            # Mandatory streaming accumulator: handles missing/spoofed Content-Length
            chunks = []
            received = 0
            async for chunk in response.aiter_bytes(chunk_size=65536):
                received += len(chunk)
                if received > MAX_FILE_BYTES:
                    raise ValueError(
                        f"Source file exceeds 10MB limit (stopped after "
                        f"{received / 1024 / 1024:.1f}MB downloaded)."
                    )
                chunks.append(chunk)

    return b"".join(chunks)


# =============================================================================
# WeasyPrint Safe URL Fetcher (SSRF Protection for Secondary Fetches)
# =============================================================================

def safe_url_fetcher(url):
    """SSRF-safe url_fetcher for WeasyPrint secondary fetches (CSS, images, @import).

    WeasyPrint fetches external resources referenced in HTML (<link>, <img>, CSS @import).
    This wrapper calls validate_url_for_ssrf on every URL before WeasyPrint fetches it,
    preventing SSRF via CVE-2025-68616 redirect bypass pattern.
    """
    validate_url_for_ssrf(url)
    return default_url_fetcher(url)


# =============================================================================
# Sync Conversion Functions (called via run_in_threadpool)
# =============================================================================

def sync_convert_image(
    file_bytes: bytes,
    fmt: str,
    width: Optional[int],
    height: Optional[int],
) -> bytes:
    """Convert/resize an image using Pillow. Sync — must be called via run_in_threadpool.

    Supports input formats: JPEG, PNG, WEBP, GIF, BMP, TIFF.
    Handles RGBA→JPEG conversion by compositing onto white background.
    Preserves aspect ratio when only one dimension is specified.
    """
    try:
        img = Image.open(BytesIO(file_bytes))
    except UnidentifiedImageError:
        raise ValueError("Not a recognized image format")

    # Decompression bomb guard — check pixel count before loading pixel data
    if img.width * img.height > MAX_PIXELS:
        raise ValueError(
            f"Image too large: {img.width}x{img.height} pixels"
            f" (max {MAX_PIXELS:,} — approximately 50MP)"
        )

    ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"}
    if img.format not in ALLOWED_INPUT_FORMATS:
        raise ValueError(f"Unsupported input format: {img.format}")

    # Force decode now so errors surface before further processing
    img.load()

    # Resize with aspect ratio preservation
    if width or height:
        orig_w, orig_h = img.size
        if width and not height:
            height = int(orig_h * width / orig_w)
        elif height and not width:
            width = int(orig_w * height / orig_h)
        img = img.resize((width, height), Image.LANCZOS)  # NOT Image.ANTIALIAS (removed in Pillow 10.0)

    # JPEG mode conversion — composite transparency onto white background
    if fmt.lower() in ("jpeg", "jpg") and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        converted = img.convert("RGBA") if img.mode == "P" else img
        background.paste(converted, mask=converted.split()[-1] if "A" in converted.mode else None)
        img = background
    elif fmt.lower() in ("jpeg", "jpg") and img.mode != "RGB":
        img = img.convert("RGB")

    out = BytesIO()
    pillow_fmt = "JPEG" if fmt.lower() == "jpg" else fmt.upper()
    save_kwargs = {"optimize": True}
    if pillow_fmt == "JPEG":
        save_kwargs["quality"] = 85
    img.save(out, format=pillow_fmt, **save_kwargs)
    return out.getvalue()


def csv_to_json(file_bytes: bytes) -> bytes:
    """Convert CSV bytes to JSON bytes. Sync — must be called via run_in_threadpool.

    Handles:
    - UTF-8 BOM (Excel/Google Sheets exports) via utf-8-sig encoding
    - Latin-1 fallback for Windows ANSI exports
    - Delimiter detection via csv.Sniffer (comma, semicolon, tab, pipe)
    - Fallback to comma dialect if Sniffer fails
    """
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # Fallback: comma-separated

    reader = csv.DictReader(StringIO(text), dialect=dialect)

    if reader.fieldnames is None:
        raise ValueError("CSV has no header row or is empty.")

    rows = list(reader)
    return json.dumps(rows, ensure_ascii=False).encode("utf-8")


def sync_html_to_pdf(file_bytes: bytes, source_url: str) -> bytes:
    """Convert HTML bytes to PDF bytes via WeasyPrint. Sync — must be called via run_in_threadpool.

    Uses safe_url_fetcher to SSRF-validate all secondary resource fetches (CSS, images, @import).
    TemporaryDirectory ensures cleanup on any exception path.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        html_string = file_bytes.decode("utf-8", errors="replace")
        doc = weasyprint.HTML(
            string=html_string,
            base_url=source_url,
            url_fetcher=safe_url_fetcher,
        )
        doc.write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()


def sync_docx_to_pdf(file_bytes: bytes) -> bytes:
    """Convert DOCX bytes to PDF bytes via mammoth + WeasyPrint.

    Pipeline: DOCX bytes -> HTML fragment (mammoth) -> full HTML document -> PDF (WeasyPrint).
    Images are embedded as base64 data URIs by mammoth — no external URL fetches occur.
    Sync — must be called via run_in_threadpool.
    """
    import mammoth
    import zipfile

    try:
        result = mammoth.convert_to_html(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise ValueError("Not a valid DOCX file (invalid ZIP archive)")
    except KeyError:
        raise ValueError("Not a valid DOCX file (missing internal document structure)")

    # Log non-fatal conversion warnings (dropped WMF images, unrecognized styles, etc.)
    for msg in result.messages:
        logger.warning("mammoth: %s", msg)

    # Wrap HTML fragment in full document with baseline CSS
    # Required: mammoth produces no CSS; without this WeasyPrint renders plain text with no layout
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: "Liberation Sans", sans-serif; font-size: 11pt; line-height: 1.4; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: 4px 8px; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 1em; margin-bottom: 0.4em; }}
p {{ margin: 0.4em 0; }}
</style>
</head>
<body>{result.value}</body>
</html>"""

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        weasyprint.HTML(
            string=html,
            url_fetcher=safe_url_fetcher,
        ).write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()


# =============================================================================
# FastAPI App + Middleware
# =============================================================================

app = FastAPI(
    title="Bismuth Conversion",
    description="File conversion: image resize/reformat, CSV→JSON, HTML→PDF, DOCX→PDF. Part of the Bismuth utility API suite for AI agents.",
    version="2.0.0",
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
    "POST /convert": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.02", network=BASE_NETWORK)],
        mime_type="application/json",
        description="Convert files (image reformat, CSV, HTML, DOCX)",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, routes=_paid_routes, server=_x402_server)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SSRFMiddleware(BaseHTTPMiddleware):
    """Pre-payment SSRF validation for POST /convert.

    Added AFTER init_x402() — LIFO ordering means this runs FIRST, before payment.
    SSRF-blocked requests return 400 with no charge to the caller.

    IMPORTANT: Path check is "/convert" — NOT "/scrape" (Phase 5 copy-paste pitfall).
    """

    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path == "/convert":
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
                # Only reject on genuine SSRF validation failures, not JSON parse errors
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


# SSRFMiddleware added LAST — LIFO means it runs FIRST (before payment check)
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
# Request Models — Pydantic Discriminated Union
# =============================================================================

BoundedHttpUrl = Annotated[
    Url,
    UrlConstraints(allowed_schemes=["http", "https"], max_length=2048),
]


class ImageConvertRequest(BaseModel):
    type: Literal["image"]
    url: BoundedHttpUrl
    format: Literal["jpeg", "png", "webp", "gif"] = "jpeg"
    width: Optional[int] = Field(None, ge=1, le=8000)
    height: Optional[int] = Field(None, ge=1, le=8000)


class CsvConvertRequest(BaseModel):
    type: Literal["csv"]
    url: BoundedHttpUrl


class HtmlConvertRequest(BaseModel):
    type: Literal["html_pdf"]
    url: BoundedHttpUrl


class DocxConvertRequest(BaseModel):
    type: Literal["docx"]
    url: BoundedHttpUrl


ConvertRequest = Annotated[
    Union[ImageConvertRequest, CsvConvertRequest, HtmlConvertRequest, DocxConvertRequest],
    Field(discriminator="type"),
]


# =============================================================================
# Routes
# =============================================================================

def load_fixture() -> dict:
    """Load and return fixture.json content."""
    with open(FIXTURE_PATH, "r") as f:
        return json.load(f)


# =============================================================================
# OpenAPI x402 v2 Extensions + Favicon
# =============================================================================

_original_openapi_fn = app.openapi


def _openapi_with_x402_v2():
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi_fn()
    schema["info"]["x-guidance"] = (
        "Bismuth Conversion — File conversion for AI agents. "
        "POST /convert with {source_type, target_type, ...} converts image formats, "
        "CSV→JSON, HTML→PDF, DOCX→PDF ($0.02 USDC on Base). "
        "Free fixture at GET /convert/test."
    )
    _paid_ops = {("/convert", "post"): "0.020000"}
    for (path, method), amount in _paid_ops.items():
        op = schema.get("paths", {}).get(path, {}).get(method)
        if op is None:
            continue
        op["x-payment-info"] = {
            "price": {"mode": "fixed", "currency": "USD", "amount": amount},
            "protocols": [{"x402": {}}],
        }
        op.setdefault("responses", {})["402"] = {"description": "Payment Required"}

    # Mark all non-paid ops with security:[] so x402scan indexes them as free resources
    for path, path_item in schema.get("paths", {}).items():
        for method in ("get", "post", "put", "delete", "patch", "options", "head"):
            op = path_item.get(method)
            if op is None:
                continue
            if (path, method) in _paid_ops:
                continue
            op["security"] = []

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
        "name": "Bismuth Conversion",
        "description": "File conversion: image resize/reformat, CSV→JSON, HTML→PDF, DOCX→PDF. Part of the Bismuth utility API suite for AI agents.",
        "apiVersion": "1.0.0",
        "network": "base",
        "resource": {
            "url": "https://x402-conversion-api-production.up.railway.app",
            "description": "Bismuth Conversion — x402 USDC micropayments on Base",
            "mimeType": "application/json",
        },
        "services": [
            {
                "name": "Convert File",
                "endpoint": "/convert",
                "method": "POST",
                "price": "$0.02",
                "description": "Convert files: image resize/reformat, CSV→JSON, HTML→PDF, DOCX→PDF",
            },
        ],
        "resources": ["POST /convert"],
        "documentation": "https://x402-conversion-api-production.up.railway.app/docs",
        "provider": {
            "name": "Bismuth",
            "url": "https://usebismuth.com",
        },
    }


@app.api_route("/", methods=["GET", "HEAD"])
async def info():
    """Service info and pricing."""
    return {
        "service": "x402-conversion-api",
        "price": "$0.02",
        "test": "/convert/test",
        "description": "Convert files: image resize/reformat, CSV→JSON, HTML→PDF, DOCX→PDF",
        "endpoints": {
            "POST /convert": "Convert a file (requires x402 USDC payment: $0.02)",
            "GET /convert/test": "Free fixture response",
            "GET /health": "Health check",
        },
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """Health check — always returns HTTP 200."""
    return {"status": "healthy"}


@app.api_route("/convert/test", methods=["GET", "HEAD"])
@limiter.limit("100/hour")
async def convert_test(request: Request):
    """Free test endpoint — returns fixture data (no conversion, no payment required).

    Rate limited at 100 requests/hour per IP.
    Use POST /convert with x402 payment for live file conversion.
    """
    return load_fixture()


@app.post("/convert")
async def convert(request: Request, body: ConvertRequest):
    """Convert a file via URL to the target format.

    Request body must include a 'type' discriminator field:
    - type: "image" — resize/reformat (PNG, JPEG, WEBP, GIF). Optional: format, width, height.
    - type: "csv" — CSV-to-JSON using stdlib DictReader with auto-detected delimiter.
    - type: "html_pdf" — HTML-to-PDF via WeasyPrint.
    - type: "docx" — DOCX-to-PDF via mammoth + WeasyPrint (content-document fidelity, not layout-preserving).

    Returns base64-encoded output with mime_type. Input URL must be public (no private IPs).
    Source file must be ≤10MB; output must be ≤8MB before base64 encoding.

    Pricing: $0.02 USDC per conversion (Base network).
    SSRF protection: private/loopback IPs rejected before payment.
    """
    source_url = str(body.url)

    # Download source file with streaming size enforcement
    try:
        file_bytes = await download_file(source_url)
    except ValueError as e:
        return {
            "success": False,
            "type": body.type,
            "error": "download_error",
            "detail": str(e),
            "warnings": [],
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "type": body.type,
            "error": "http_error",
            "detail": f"Source URL returned HTTP {e.response.status_code}.",
            "warnings": [],
        }
    except Exception as e:
        logger.error(f"Unexpected download error for {source_url}: {e}")
        return {
            "success": False,
            "type": body.type,
            "error": "download_error",
            "detail": str(e),
            "warnings": [],
        }

    # Dispatch conversion by type — all sync converters run in threadpool
    try:
        if body.type == "image":
            output_bytes = await run_in_threadpool(
                sync_convert_image, file_bytes, body.format, body.width, body.height
            )
            mime_type = MIME_TYPES[body.format]
        elif body.type == "csv":
            output_bytes = await run_in_threadpool(csv_to_json, file_bytes)
            mime_type = "application/json"
        elif body.type == "html_pdf":
            output_bytes = await run_in_threadpool(sync_html_to_pdf, file_bytes, source_url)
            mime_type = "application/pdf"
        elif body.type == "docx":
            output_bytes = await run_in_threadpool(sync_docx_to_pdf, file_bytes)
            mime_type = "application/pdf"
    except Exception as e:
        return {
            "success": False,
            "type": body.type,
            "error": "conversion_error",
            "detail": str(e),
            "warnings": [],
        }

    # Output size guard before base64 encoding (saves ~33% memory on large outputs)
    if len(output_bytes) > MAX_OUTPUT_BYTES:
        return {
            "success": False,
            "type": body.type,
            "error": "output_too_large",
            "detail": (
                f"Output ({len(output_bytes) / 1024 / 1024:.1f}MB) exceeds 8MB limit."
            ),
            "warnings": [],
        }

    encoded = base64.b64encode(output_bytes).decode("ascii")
    return {
        "success": True,
        "type": body.type,
        "mime_type": mime_type,
        "data": encoded,
        "warnings": [],
    }
