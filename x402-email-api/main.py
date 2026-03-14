"""
x402 Email API
Transactional email via Resend — accepts to, subject, body (plain text or HTML).
Per-wallet daily rate limiting. Per-domain daily limiting. PII-safe send event logging.
Free test endpoint. Gated behind x402 USDC payment.
"""

import os
import hashlib
import logging
import threading
from datetime import date
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from fastapi_x402 import init_x402, pay
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


# =============================================================================
# Per-Wallet Daily Rate Limiter (wallet-level + domain-level)
# =============================================================================

_wallet_counts: dict = {}          # {wallet_addr_lower: (count, date)}
_wallet_domain_counts: dict = {}   # {(wallet, domain): (count, date)}
_wallet_lock = threading.Lock()    # ONE lock for both dicts — prevents deadlock


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

class EmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=998,
                         description="Email subject (max 998 chars per RFC 5321)")
    body: str = Field(..., min_length=1, max_length=102400,
                      description="Email body — HTML or plain text (max 100 KB)")
    reply_to: Optional[EmailStr] = Field(None,
                                          description="Optional reply-to address")


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
    title="x402 Email API",
    description="Transactional email via Resend — plain text or HTML body. Powered by x402 USDC payment.",
    version="1.0.0",
    lifespan=lifespan,
)

init_x402(app, network="base")  # Added FIRST -> runs LAST (LIFO)

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

@app.get("/")
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


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "resend": "configured" if resend.api_key else "not configured",
    }


@app.get("/send/test")
@limiter.limit("100/hour")
async def send_test(request: Request):
    return {"message_id": "test_00000000-0000-0000-0000-000000000000"}


@app.post("/send")
@pay("$0.01")
def send_email(request: Request, body: EmailRequest):
    """Send email via Resend. Plain def (not async def) — Resend SDK is synchronous.
    FastAPI auto-routes sync handlers to thread pool, preventing event-loop blocking.
    """
    wallet = get_wallet_address(request)
    check_and_increment_wallet_limit(wallet)
    check_and_increment_domain_limit(wallet, str(body.to))
    result = _do_send(body)
    log_send_event(
        wallet or "unknown",
        str(body.to),
        body.subject,
        result["id"],
    )
    return {"message_id": result["id"]}
