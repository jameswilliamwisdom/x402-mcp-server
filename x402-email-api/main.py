"""
x402 Email API
Transactional email via Resend — accepts to, subject, body (plain text or HTML).
Per-wallet daily rate limiting. Per-domain daily limiting. PII-safe send event logging.
Free test endpoint. Gated behind x402 USDC payment.
"""

import os
import base64
import hashlib
import logging
import mimetypes
import re
import threading
from datetime import date
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

import resend
from resend.exceptions import ResendError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# Logger and Constants
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x402-email")

DAILY_SEND_LIMIT = 10
DAILY_DOMAIN_LIMIT = 5
FROM_ADDRESS = "x402 Email API <noreply@jameswisdom.ink>"
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25MB pre-encoding cap
MIME_TYPE_PATTERN = re.compile(
    r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]*$'
)


# =============================================================================
# Per-Wallet Daily Rate Limiter (wallet-level + domain-level)
# =============================================================================

_wallet_counts: dict = {}          # {wallet_addr_lower: (count, date)}
_wallet_domain_counts: dict = {}   # {(wallet, domain): (count, date)}
_wallet_lock = threading.Lock()    # ONE lock for both dicts — prevents deadlock


def get_wallet_address(request: Request):
    """Extract payer wallet from x402 v2 middleware state.

    x402[fastapi,evm] middleware (v2.16+) stores the verified payment on:
        request.state.payment_payload  # PaymentPayload model
    Whose .payload dict (for the exact-evm scheme) is the serialized
    ExactEIP3009Payload:
        {"authorization": {"from": "0x...", ...}, "signature": "0x..."}

    Returns lowercased buyer address or None if unavailable (which disables
    per-wallet limits — fail open for pre-payment probes).
    """
    payment_payload = getattr(request.state, "payment_payload", None)
    if payment_payload is None:
        return None
    try:
        # payment_payload is a Pydantic model; .payload is dict[str, Any]
        payload = payment_payload.payload if hasattr(payment_payload, "payload") else payment_payload["payload"]
        return payload["authorization"]["from"].lower()
    except (KeyError, TypeError, AttributeError):
        return None


def check_and_increment_wallet_limit(wallet) -> None:
    """Check daily wallet limit and increment counter atomically.
    Raises HTTP 429 if limit reached. No-op if wallet is None.
    Increment BEFORE calling Resend — prevents quota manipulation via induced failures.
    """
    if wallet is None:
        return
    today = date.today()
    with _wallet_lock:
        count, recorded_day = _wallet_counts.get(wallet, (0, today))
        if recorded_day != today:
            count = 0  # New day — reset
        if count >= DAILY_SEND_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "wallet_limit_exceeded",
                    "limit": DAILY_SEND_LIMIT,
                    "resets": "midnight UTC",
                },
            )
        _wallet_counts[wallet] = (count + 1, today)


def check_and_increment_domain_limit(wallet, to_address: str) -> None:
    """Per-wallet per-domain daily limit. Prevents hammering one domain.
    Increment BEFORE calling Resend — prevents quota manipulation via induced failures.
    """
    if wallet is None:
        return
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    today = date.today()
    key = (wallet, domain)
    with _wallet_lock:  # Reuse same lock — one lock for all wallet state
        count, recorded_day = _wallet_domain_counts.get(key, (0, today))
        if recorded_day != today:
            count = 0  # New day — reset
        if count >= DAILY_DOMAIN_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "domain_limit_exceeded",
                    "limit": DAILY_DOMAIN_LIMIT,
                    "domain": domain,
                    "resets": "midnight UTC",
                },
            )
        _wallet_domain_counts[key] = (count + 1, today)


# =============================================================================
# PII-Safe Send Event Logging
# =============================================================================

def log_send_event(wallet: str, to_address: str, subject: str, message_id: str) -> None:
    """Log send event with PII-safe fields. Never log full recipient or subject text."""
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()[:16]
    logger.info(
        "send_event wallet=%s domain=%s subject_hash=%s message_id=%s",
        wallet, domain, subject_hash, message_id,
    )


# =============================================================================
# Pydantic Request Model
# =============================================================================

class AttachmentItem(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255,
                          description="Attachment filename including extension")
    content: str = Field(..., description="Base64-encoded file content")
    content_type: Optional[str] = Field(
        None,
        description="MIME type — auto-derived from filename if omitted"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        v = os.path.basename(v.replace("\\", "/"))
        if any(ord(c) < 32 for c in v):
            raise ValueError("filename contains control characters")
        if not v:
            raise ValueError("filename is empty after sanitization")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_mime_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not MIME_TYPE_PATTERN.match(v):
            raise ValueError("content_type must be a valid MIME type (e.g. application/pdf)")
        return v

    @field_validator("content")
    @classmethod
    def validate_attachment_size(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("attachment content is not valid base64")
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment exceeds 25MB limit "
                f"({len(raw) / 1024 / 1024:.1f}MB decoded)"
            )
        return v


class EmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=998,
                         description="Email subject (max 998 chars per RFC 5321)")
    body: str = Field(..., min_length=1, max_length=102400,
                      description="Email body — HTML or plain text (max 100 KB)")
    reply_to: Optional[EmailStr] = Field(None,
                                          description="Optional reply-to address")
    cc: Optional[List[EmailStr]] = Field(
        None,
        description="Carbon copy recipients"
    )
    bcc: Optional[List[EmailStr]] = Field(
        None,
        description="Blind carbon copy recipients"
    )
    attachments: Optional[List[AttachmentItem]] = Field(
        None,
        description="Base64-encoded file attachments (25MB pre-encoding cap per file)"
    )


# =============================================================================
# HTML vs. Plain Text Body Classifier and Send Params Builder
# =============================================================================

def build_send_params(body: EmailRequest) -> dict:
    """Classify body as HTML or plain text and build Resend SDK params.
    For HTML bodies, omit 'text' key entirely — Resend auto-generates plain-text server-side.
    CRITICAL: Never include "html": None or "text": None — Resend treats null differently from absent key.
    """
    stripped = body.body.strip()
    is_html = stripped.startswith("<") and ("</" in stripped or "/>" in stripped)

    params: resend.Emails.SendParams = {
        "from": FROM_ADDRESS,
        "to": [str(body.to)],      # MUST be list[str], not bare str
        "subject": body.subject,
    }

    if is_html:
        params["html"] = body.body
        # Omit "text" — Resend auto-generates plain-text from html server-side
    else:
        params["text"] = body.body
        # Omit "html" when sending plain text

    if body.reply_to:
        params["reply_to"] = str(body.reply_to)

    # CC recipients
    if body.cc:
        params["cc"] = [str(addr) for addr in body.cc]

    # BCC recipients
    if body.bcc:
        params["bcc"] = [str(addr) for addr in body.bcc]

    # Attachments — pass base64 string directly to Resend SDK
    if body.attachments:
        resend_attachments = []
        for att in body.attachments:
            attachment: resend.Attachment = {
                "filename": att.filename,
                "content": att.content,  # base64 str — SDK accepts Union[List[int], str]
            }
            # Auto-derive content_type from filename if caller omitted it
            if att.content_type:
                attachment["content_type"] = att.content_type
            else:
                guessed, _ = mimetypes.guess_type(att.filename)
                if guessed:
                    attachment["content_type"] = guessed
            resend_attachments.append(attachment)
        params["attachments"] = resend_attachments

    return params


# =============================================================================
# Resend Send Function with Error Handling
# =============================================================================

def _do_send(body: EmailRequest) -> dict:
    """Send email via Resend SDK. Maps SDK exceptions to HTTP status codes."""
    params = build_send_params(body)
    try:
        result = resend.Emails.send(params)
        return result
    except ResendError as e:
        code = getattr(e, "code", 500)
        error_type = getattr(e, "error_type", "")
        message = getattr(e, "message", str(e))

        # Resend account-level quota exhaustion — not the caller's fault
        if error_type in ("daily_quota_exceeded", "monthly_quota_exceeded"):
            raise HTTPException(503, detail="Email service quota reached. Try again later.")

        # Resend's 2 req/sec account-level rate limit
        if error_type == "rate_limit_exceeded":
            raise HTTPException(503, detail="Email service temporarily busy. Try again in a few seconds.")

        # Auth/config errors — operator must fix
        if int(code) in (401, 403):
            logger.error("Resend auth/config error: %s — %s", error_type, message)
            raise HTTPException(500, detail="Email service misconfigured.")

        # All other Resend errors
        raise HTTPException(500, detail=f"Email delivery failed: {message}")


# =============================================================================
# Lifespan — Set Resend API Key
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — email endpoint will fail")
    resend.api_key = api_key  # Module-level global, set once at startup
    yield


# =============================================================================
# FastAPI App Setup
# =============================================================================

app = FastAPI(
    title="Bismuth Email",
    description="Transactional email via Resend with CC/BCC and base64 file attachments. Part of the Bismuth utility API suite for AI agents.",
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
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.daydreams.systems")

_facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
_x402_server = x402ResourceServer(_facilitator)
_x402_server.register(BASE_NETWORK, ExactEvmServerScheme())

_paid_routes = {
    "POST /send": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.01", network=BASE_NETWORK)],
        mime_type="application/json",
        description="Send transactional email via Resend",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, routes=_paid_routes, server=_x402_server)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# No SSRFMiddleware — email API has no outbound URL fetching from user input.
# The only outbound call is to api.resend.com, a trusted third-party.


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
# Route Handlers
# =============================================================================

# =============================================================================
# OpenAPI x402 v2 Extensions
# =============================================================================

_original_openapi_fn = app.openapi


def _openapi_with_x402_v2():
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi_fn()

    schema["info"]["x-guidance"] = (
        "Bismuth Email — Transactional email delivery via Resend for AI agents. "
        "POST /send with {to, subject, body, cc?, bcc?, attachments?} sends an email "
        "($0.01 USDC on Base). Attachments are base64-encoded, 25MB cap per file. "
        "Per-wallet daily rate limits apply. Free test at GET /send/test."
    )

    _paid_ops = {("/send", "post"): "0.010000"}
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
        "name": "Bismuth Email",
        "description": "Transactional email via Resend with CC/BCC and base64 file attachments. Part of the Bismuth utility API suite for AI agents.",
        "apiVersion": "1.0.0",
        "network": "base",
        "resource": {
            "url": "https://x402-email-api-production.up.railway.app",
            "description": "Bismuth Email — x402 USDC micropayments on Base",
            "mimeType": "application/json",
        },
        "services": [
            {
                "name": "Send Email",
                "endpoint": "/send",
                "method": "POST",
                "price": "$0.01",
                "description": "Send transactional email (plain text or HTML) with optional CC, BCC, and attachments",
            },
        ],
        "resources": ["POST /send"],
        "documentation": "https://x402-email-api-production.up.railway.app/docs",
        "provider": {
            "name": "Bismuth",
            "url": "https://usebismuth.com",
        },
    }


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "service": "x402-email-api",
        "price": "$0.01",
        "test": "/send/test",
        "description": "Transactional email via Resend — plain text or HTML body",
        "endpoints": {
            "POST /send": "Send email (requires x402 USDC payment: $0.01)",
            "GET /send/test": "Free test response (no real email sent)",
            "GET /health": "Health check",
        },
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {
        "status": "healthy",
        "resend": "configured" if resend.api_key else "not configured",
    }


@app.api_route("/send/test", methods=["GET", "HEAD"])
@limiter.limit("100/hour")
async def send_test(request: Request):
    return {"message_id": "test_00000000-0000-0000-0000-000000000000"}


@app.post("/send")
def send_email(request: Request, body: EmailRequest):
    """Send email via Resend. Plain def (not async def) — Resend SDK is synchronous.
    FastAPI auto-routes sync handlers to thread pool, preventing event-loop blocking.
    """
    wallet = get_wallet_address(request)
    check_and_increment_wallet_limit(wallet)
    # Rate-limit all recipients — to + cc + bcc (Pitfall #4: CC/BCC bypass)
    all_recipients = [str(body.to)]
    if body.cc:
        all_recipients.extend(str(addr) for addr in body.cc)
    if body.bcc:
        all_recipients.extend(str(addr) for addr in body.bcc)
    for recipient in all_recipients:
        check_and_increment_domain_limit(wallet, recipient)
    result = _do_send(body)
    log_send_event(
        wallet or "unknown",
        str(body.to),
        body.subject,
        result["id"],
    )
    return {"message_id": result["id"]}
