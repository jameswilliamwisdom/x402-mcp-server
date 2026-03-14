# Phase 8: Email Sending API - Research

**Researched:** 2026-03-14
**Domain:** Transactional Email (Resend SDK, FastAPI, x402 payment gate)
**Confidence:** HIGH
**Method:** MECE decomposition (3 dimensions: INTEGRATION, SECURITY, PITFALLS)

---

## Summary

Phase 8 builds a new Railway service (`x402-email-api`) that sends transactional email via the Resend HTTP API. The implementation is a direct extension of the Phases 5–7 pattern: FastAPI + fastapi-x402 + per-wallet rate limiting. No novel architecture is introduced.

The central integration decision is that the Resend Python SDK (`resend>=2.0.0,<3.0.0`) is **synchronous-only** — it uses `requests` internally with a 30-second timeout. The correct mitigation is to declare the send route as a plain `def` function (not `async def`), which causes FastAPI to automatically run it in a thread pool without event-loop blocking. No additional wrapper is needed.

The other key simplification is that **Resend automatically generates a plain-text fallback from the HTML body server-side** when the `text` parameter is omitted from the SDK call. There is no need to import `html2text` or any HTML conversion library. The only classification the code needs to perform is whether the body is HTML or plain text, so the correct `html` vs `text` SDK parameter is populated.

Security follows the established project pattern exactly: per-wallet in-memory counter protected by `threading.Lock`, wallet address extracted from `decoded_payment["payload"]["authorization"]["from"].lower()`, and PII-safe logging (domain only, not full email address; subject hash not subject text). The x402 payment gate ($0.01/send) is the primary spam deterrent; the 10-sends/day per-wallet limit is the secondary cap.

**Primary recommendation:** Use the Resend SDK with a plain `def` route handler, omit the `text` param for HTML bodies to let Resend auto-generate it, and copy the per-wallet rate limiting pattern from Phase 7 (`x402-search-api/main.py`) verbatim.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Sender Identity
- Domain: `jameswisdom.ink` — verified via Resend (Cloudflare DNS, all records propagated)
- From address: `x402 Email API <noreply@jameswisdom.ink>`
- Optional `reply_to` parameter — caller can set a reply-to address so recipients can respond to them directly
- From address is hardcoded, not user-configurable

#### Email Content
- Accept HTML body with auto-generated plain-text fallback (matches roadmap spec)
- No file attachments in v1 — defer to v1.2
- Pass HTML through raw to Resend — email clients don't execute scripts; Resend handles reputation

#### Claude's Discretion
- Max body size limit — pick a reasonable ceiling for transactional email
- HTML sanitization approach — decide based on security best practices
- Per-recipient rate limit — decide whether to add one beyond the per-wallet limit, based on threat model for micropayment-gated APIs

#### Abuse Prevention
- Email format validation only (regex) — Resend handles deliverability/bounces
- No content-based filtering — the USDC payment gate ($0.01+/email) is the economic spam deterrent
- Send logs to stdout/Railway logs (wallet address, recipient domain, subject hash) — server-side only, no queryable endpoint
- Per-wallet rate limit: 10 sends/day (from roadmap)

#### Resend Configuration
- Resend free tier (100 emails/day, 1 domain) — sufficient for micropayment-gated API
- Domain: `jameswisdom.ink` on Cloudflare DNS — SPF/DKIM/DMARC verified and propagated
- Resend account: created (jameswilliamwisdom)
- Resend API key: set as `RESEND_API_KEY` Railway env var (create via Resend dashboard → API Keys)

### Deferred Ideas (OUT OF SCOPE)

- File attachments — v1.2
- Queryable audit log endpoint — future phase if needed
- Multiple sender domains — future phase
- Email templates / merge tags — future phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EMAIL-01 | Send email with to, subject, plain text body via Resend | Resend SDK `resend.Emails.send()` with `text` param. `SendParams` TypedDict pattern confirmed. Plain `def` route prevents event-loop blocking. [INTEGRATION, PITFALLS] |
| EMAIL-02 | HTML body support with auto plain-text fallback | Resend auto-generates `text` from `html` server-side when `text` param is omitted — no library needed. Body-type classifier (`html` vs `text` param selection) required. [PITFALLS] |
| EMAIL-03 | Verified sender domain with SPF/DKIM/DMARC configured | `jameswisdom.ink` already verified per CONTEXT.md. Hardcode `"from": "x402 Email API <noreply@jameswisdom.ink>"` in SendParams. Domain propagation delay pitfall documented. [INTEGRATION, PITFALLS] |
| EMAIL-04 | Abuse limits — rate limit per wallet (10 sends/day) | Per-wallet in-memory counter + `threading.Lock`, copied from Phase 7. `DAILY_SEND_LIMIT = 10`. Wallet path: `decoded_payment["payload"]["authorization"]["from"].lower()`. [SECURITY] |
| EMAIL-05 | Free test endpoint (sandbox mode, no real delivery) | `GET /send/test` returns static fake message ID. `slowapi` IP-based rate limit (`100/hour`). No Resend call. [INTEGRATION, SECURITY] |
</phase_requirements>

---

## Standard Stack

| Library | Version | Purpose |
|---------|---------|---------|
| `resend` | `>=2.0.0,<3.0.0` | Official Resend Python SDK — wraps the Resend HTTPS API for email sending. Latest: 2.23.0 (2026-02-23). |
| `pydantic[email]` | `>=2.0.0` (with `email-validator` extra) | Request/response validation. `EmailStr` field type for RFC 5322-compliant address validation. |
| `fastapi` | `>=0.100.0` | Existing web framework (Phases 5–7). |
| `fastapi-x402` | `>=0.1.8` | Existing x402 payment middleware (Phases 5–7). |
| `uvicorn[standard]` | `>=0.23.0` | Existing ASGI server (Phases 5–7). |
| `slowapi` | `>=0.1.9` | Existing IP-based rate limiter for free test endpoint (Phases 5–7). |

**No new heavy dependencies.** The Resend SDK pulls in only `requests>=2.31.0` and `typing-extensions>=4.4.0`. The `html2text` library is **not needed** — Resend generates plain-text server-side automatically.

`requirements.txt`:
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic[email]>=2.0.0
fastapi-x402>=0.1.8
resend>=2.0.0,<3.0.0
slowapi>=0.1.9
```

**Install:**
```bash
pip install resend>=2.0.0 "pydantic[email]>=2.0.0"
```

---

## Architecture Patterns

### Pattern 1: Plain `def` Route for Blocking SDK (Not `async def`)

The Resend Python SDK uses `requests` (synchronous blocking I/O) with a 30-second default timeout. The correct FastAPI pattern is to declare the send route as a plain `def` function — FastAPI automatically runs sync routes in a thread pool, preventing event-loop blocking. This is simpler than wrapping in `run_in_threadpool`.

```python
# Correct — FastAPI runs this in a thread pool automatically
@app.post("/send")
@pay("$0.01")
def send_email(request: Request, body: EmailRequest):
    wallet = get_wallet_address(request)
    check_and_increment_wallet_limit(wallet)
    result = _do_send(body)
    log_send_event(wallet, body.to, body.subject, result["id"])
    return {"message_id": result["id"]}
```

Note: `request.state.decoded_payment` is still accessible in a plain `def` route — fastapi-x402 injects it before the route runs regardless of sync/async.

### Pattern 2: Module-Level Global API Key Initialization

The Resend SDK has no client object — authentication is a module-level global set once at startup.

```python
import os
import resend
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

logger = logging.getLogger("x402-email")

@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — email endpoint will fail")
    resend.api_key = api_key  # Module-level global, set once
    yield

app = FastAPI(title="x402 Email API", lifespan=lifespan)
```

### Pattern 3: HTML vs. Plain Text Body Classification

Detect whether the incoming `body` field is HTML and set SDK params accordingly. For HTML bodies, omit `text` entirely — Resend generates it server-side.

```python
def build_send_params(body: EmailRequest) -> dict:
    stripped = body.body.strip()
    is_html = stripped.startswith("<") and ("</" in stripped or "/>" in stripped)

    params: resend.Emails.SendParams = {
        "from": "x402 Email API <noreply@jameswisdom.ink>",
        "to": [body.to],          # Always list[str]
        "subject": body.subject,
    }

    if is_html:
        params["html"] = body.body
        # Omit "text" key entirely — Resend auto-generates plain-text from html
    else:
        params["text"] = body.body
        # Omit "html" key entirely when sending plain text

    if body.reply_to:
        params["reply_to"] = body.reply_to

    return params
```

**Critical:** Do not include `"html": None` or `"text": None` in SendParams. Resend treats a `null` value differently from an absent key. Only include a key when the value is a non-null string.

### Pattern 4: Per-Wallet Rate Limiting (Verbatim from Phase 7)

```python
import threading
from datetime import date
from fastapi import HTTPException

_wallet_counts: dict = {}         # {wallet_addr: (count, date)}
_wallet_domain_counts: dict = {}  # {(wallet, domain): (count, date)}
_wallet_lock = threading.Lock()
DAILY_SEND_LIMIT = 10
DAILY_DOMAIN_LIMIT = 5

def get_wallet_address(request: Request) -> str:
    decoded = request.state.decoded_payment
    return decoded["payload"]["authorization"]["from"].lower()

def check_and_increment_wallet_limit(wallet: str) -> None:
    today = date.today()
    with _wallet_lock:
        count, recorded_day = _wallet_counts.get(wallet, (0, today))
        if recorded_day != today:
            count = 0
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

def check_and_increment_domain_limit(wallet: str, to_address: str) -> None:
    """Per-wallet per-domain daily limit: 5 sends to same domain."""
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    today = date.today()
    key = (wallet, domain)
    with _wallet_lock:  # Reuse same lock — both dicts, one lock
        count, recorded_day = _wallet_domain_counts.get(key, (0, today))
        if recorded_day != today:
            count = 0
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
```

**Key invariant:** Increment BEFORE the Resend API call. Prevents quota manipulation via induced failures.

### Pattern 5: Resend Error Handling

Resend SDK raises `resend.exceptions.ResendError` subclasses on non-2xx responses. Catch by base class and inspect `e.code`/`e.error_type`:

```python
from resend.exceptions import ResendError, RateLimitError as ResendRateLimitError

def _do_send(body: EmailRequest) -> dict:
    params = build_send_params(body)
    try:
        result = resend.Emails.send(params)
        return result
    except ResendRateLimitError as e:
        if getattr(e, "error_type", "") in ("daily_quota_exceeded", "monthly_quota_exceeded"):
            raise HTTPException(503, detail="Email service quota reached. Try again later.")
        raise HTTPException(429, detail="Rate limit exceeded.")
    except ResendError as e:
        if int(e.code) in (401, 403):
            logger.error(f"Resend auth/config error: {e.error_type} — {e.message}")
            raise HTTPException(500, detail="Email service misconfigured.")
        raise HTTPException(500, detail=f"Email delivery failed: {e.message}")
```

**Error → HTTP status mapping:**

| Resend Error | HTTP Status | Rationale |
|---|---|---|
| `missing_api_key` / `invalid_api_key` | 500 | Operator config issue, not caller fault |
| `validation_error` (unverified domain) | 500 | Hardcoded domain — operator must fix |
| `invalid_from_address` | 500 | Hardcoded from — operator must fix |
| `missing_required_field` | Caught by Pydantic (422) before Resend is called | — |
| `daily_quota_exceeded` / `monthly_quota_exceeded` | 503 | Service-level limit, not the caller's wallet |
| `rate_limit_exceeded` | 503 | Resend's 2 req/sec account limit |
| `application_error` / `internal_server_error` | 502 | Upstream failure |

### Pattern 6: PII-Safe Send Event Logging

```python
import hashlib
import logging

logger = logging.getLogger("x402-email")

def log_send_event(wallet: str, to_address: str, subject: str, message_id: str) -> None:
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()[:16]
    logger.info(
        "send_event wallet=%s domain=%s subject_hash=%s message_id=%s",
        wallet, domain, subject_hash, message_id,
    )
```

Log AFTER successful Resend response (after receiving `message_id`). Never log the full recipient address or subject text.

### Pattern 7: Free Test Endpoint

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/send/test")
@limiter.limit("100/hour")
async def send_test(request: Request):
    # No Resend call — returns static fake message ID
    return {"message_id": "test_00000000-0000-0000-0000-000000000000"}
```

No fixture.json needed — the email response is a single field. Return inline.

### Pattern 8: Pydantic Request Model

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class EmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=998, description="Email subject (max 998 chars per RFC 5321)")
    body: str = Field(..., min_length=1, max_length=102400, description="Email body (HTML or plain text, max 100 KB)")
    reply_to: Optional[EmailStr] = Field(None, description="Optional reply-to address")
```

`EmailStr` performs RFC 5322 format validation before the route handler runs. `pydantic[email]` extra must be installed. Body cap is 100 KB (102400 bytes) — sufficient for all transactional use cases.

### Pattern 9: Middleware Order

```python
app = FastAPI(title="x402 Email API", lifespan=lifespan)
init_x402(app, network="base")         # Added first → runs last (LIFO)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
# No SSRFMiddleware — email API has no outbound URL fetching from user input
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML → plain text conversion | `html2text`, BeautifulSoup strippers, regex | **Nothing** — omit `text` param in SDK call | Resend auto-generates `text` from `html` server-side. Confirmed in Resend changelog "Automatic Plain Text Emails." Custom converters are unnecessary complexity. |
| Email address format validation | Custom regex | `pydantic[email]` (`EmailStr`) | RFC 5321/5322 address parsing has many edge cases (quoted strings, IP literals, internationalized domains). `email-validator` handles them all. |
| x402 payment verification | Custom JWT/signature parsing | `fastapi-x402` `@pay` decorator | EIP-712 typed data signing has subtle validation requirements. The established pattern works. |
| Thread-safe counters | Custom counter class / Redis | `threading.Lock` + plain dict | Already proven in Phases 6 and 7. Don't introduce new dependencies for a 10/day limit. |
| MIME message construction | `email.mime.*` multipart assembly | Resend SDK `html`/`text` params | Resend handles MIME assembly, Content-Type headers, multipart boundaries, and text/html alternatives. |
| HTML body sanitization | `bleach`, `lxml` cleaner | Pass HTML raw to Resend | User decision: "Pass HTML through raw — email clients don't execute scripts; Resend handles reputation." |
| Retry logic on transient failures | Custom exponential backoff | Fail-fast with clear error | Retry loops can trigger Resend's 2 req/sec account-level rate limit. Return 503 immediately and let callers retry. |
| SMTP delivery | `smtplib`, `aiosmtplib` | Resend HTTPS API only | Railway blocks SMTP ports (25, 465, 587, 2525) on Hobby plan at the network level. HTTPS-only Resend API is the only viable path. |

---

## Common Pitfalls

### Pitfall 1: `async def` Route Blocks the Event Loop

Calling `resend.Emails.send()` inside an `async def` handler blocks FastAPI's event loop for ~200–500ms per send. Under load this serializes all requests. **Fix:** Declare the route as plain `def` — FastAPI auto-routes it to a thread pool.

### Pitfall 2: Including `"html": None` or `"text": None` in SendParams

Resend treats a null value differently from an absent key. Passing `"html": None` may trigger a `validation_error`. **Fix:** Only include `"html"` or `"text"` in the params dict when the value is a non-empty string. Build params conditionally.

### Pitfall 3: `to` as String Instead of `list[str]`

The API enforces `to` as an array. Passing a bare string causes a `422 validation_error`. **Fix:** Always coerce: `"to": [body.to] if isinstance(body.to, str) else body.to`.

### Pitfall 4: `from`, `subject` Are `NotRequired` in TypedDict But Required by API

`resend.Emails.SendParams` marks only `to` as `__required_keys__`. Type checkers will not warn if `from` or `subject` are missing, but the API returns `422 missing_required_fields` at runtime. **Fix:** Always include `from`, `to`, `subject`, and `html`/`text` explicitly. Don't rely on type hints.

### Pitfall 5: Logging Full Recipient Address

`logger.info("sent to %s", to_address)` exposes PII in Railway logs. **Fix:** Log only the domain (`to_address.split("@")[-1]`), never the full address.

### Pitfall 6: Logging Before Resend Confirms Delivery

Logging immediately after constructing params (before `resend.Emails.send()` returns) creates misleading audit trails for sends that never went out. **Fix:** Log only after receiving a `message_id` from a successful Resend response.

### Pitfall 7: Two Separate Locks for `_wallet_counts` and `_wallet_domain_counts`

Separate lock instances create potential deadlock if different code paths acquire them in different orders. **Fix:** Use one shared `_wallet_lock` for all in-memory wallet state.

### Pitfall 8: EIP-55 Wallet Address Case Split

Checksum addresses (`0xABCD...`) and lowercase hex (`0xabcd...`) are the same wallet but compare as different strings, splitting the count. **Fix:** Always `.lower()` the wallet at extraction time.

### Pitfall 9: Domain Verification Propagation Delay

Resend's UI may show "Verified" for a domain before the internal state fully propagates. Sends within this window get `403 validation_error` with "domain not verified." **Fix:** Test with a live send immediately after UI shows green — if 403, wait 15–30 minutes. (Note: `jameswisdom.ink` is already verified and propagated per CONTEXT.md. Include a test-send step in the deployment checklist regardless.)

### Pitfall 10: Resend Free Tier Quota Poisons All Wallets

Resend's 100 emails/day free tier limit is account-wide. When it's hit, all wallets receive errors regardless of their individual count. **Fix:** Catch `ResendRateLimitError` with quota error types and return HTTP 503 (service unavailable), not 429 — the individual caller is not at fault.

### Pitfall 11: `RESEND_API_KEY` Not Set Raises on First Request

`MissingApiKeyError` is raised at call time, not at import. A missing env var silently passes startup. **Fix:** Check the env var in the lifespan function and log a warning if absent. The Railway env var must be set before the service starts.

### Pitfall 12: In-Memory Counts Reset on Redeploy

Rate limit counters reset to zero on every Railway redeploy. In development this makes the 10-send limit appear non-functional. **Fix:** Document this behavior. Test the rate limit within a single running instance session, not across restarts.

### Pitfall 13: Railway Blocks SMTP

Outbound SMTP ports (25, 465, 587, 2525) are blocked on Railway Hobby plan. This phase correctly uses Resend's HTTPS API and is unaffected, but this forecloses any SMTP-based fallback in future changes.

### Pitfall 14: `reply_to` Display-Name Format

Passing `"John Doe <john@example.com>"` as `reply_to` instead of `"john@example.com"` may cause parsing inconsistencies across email clients. **Fix:** Validate `reply_to` with the same `EmailStr` validator used for `to` — `EmailStr` rejects display-name format.

### Pitfall 15: Resend's 2 req/sec Account-Level Rate Limit

Distinct from the per-wallet daily limit. Retry loops can trigger this. **Fix:** Fail fast on Resend errors; return 503 and let callers apply their own retry backoff.

---

## Code Examples

### Complete Route Handler

```python
import os
import hashlib
import logging
import threading
import resend
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi_x402 import init_x402, pay
from resend.exceptions import ResendError, RateLimitError as ResendRateLimitError

logger = logging.getLogger("x402-email")
limiter = Limiter(key_func=get_remote_address)

# --- Rate limit state ---
_wallet_counts: dict = {}
_wallet_domain_counts: dict = {}
_wallet_lock = threading.Lock()
DAILY_SEND_LIMIT = 10
DAILY_DOMAIN_LIMIT = 5

# --- Pydantic model ---
class EmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1, max_length=102400)
    reply_to: Optional[EmailStr] = None

# --- Startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — email endpoint will fail")
    resend.api_key = api_key
    yield

app = FastAPI(title="x402 Email API", lifespan=lifespan)
init_x402(app, network="base")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.state.limiter = limiter

# --- Helpers ---
def get_wallet_address(request: Request) -> str:
    decoded = request.state.decoded_payment
    return decoded["payload"]["authorization"]["from"].lower()

def check_and_increment_wallet_limit(wallet: str) -> None:
    today = date.today()
    with _wallet_lock:
        count, recorded_day = _wallet_counts.get(wallet, (0, today))
        if recorded_day != today:
            count = 0
        if count >= DAILY_SEND_LIMIT:
            raise HTTPException(429, detail={"error": "wallet_limit_exceeded", "limit": DAILY_SEND_LIMIT, "resets": "midnight UTC"})
        _wallet_counts[wallet] = (count + 1, today)

def check_and_increment_domain_limit(wallet: str, to_address: str) -> None:
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    today = date.today()
    key = (wallet, domain)
    with _wallet_lock:
        count, recorded_day = _wallet_domain_counts.get(key, (0, today))
        if recorded_day != today:
            count = 0
        if count >= DAILY_DOMAIN_LIMIT:
            raise HTTPException(429, detail={"error": "domain_limit_exceeded", "limit": DAILY_DOMAIN_LIMIT, "domain": domain, "resets": "midnight UTC"})
        _wallet_domain_counts[key] = (count + 1, today)

def log_send_event(wallet: str, to_address: str, subject: str, message_id: str) -> None:
    domain = to_address.split("@")[-1].lower() if "@" in to_address else "unknown"
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()[:16]
    logger.info("send_event wallet=%s domain=%s subject_hash=%s message_id=%s", wallet, domain, subject_hash, message_id)

def build_send_params(body: EmailRequest) -> dict:
    stripped = body.body.strip()
    is_html = stripped.startswith("<") and ("</" in stripped or "/>" in stripped)
    params: resend.Emails.SendParams = {
        "from": "x402 Email API <noreply@jameswisdom.ink>",
        "to": [str(body.to)],
        "subject": body.subject,
    }
    if is_html:
        params["html"] = body.body
        # Omit "text" — Resend auto-generates plain-text from html server-side
    else:
        params["text"] = body.body
    if body.reply_to:
        params["reply_to"] = str(body.reply_to)
    return params

def _do_send(body: EmailRequest) -> dict:
    params = build_send_params(body)
    try:
        return resend.Emails.send(params)
    except ResendRateLimitError as e:
        if getattr(e, "error_type", "") in ("daily_quota_exceeded", "monthly_quota_exceeded"):
            raise HTTPException(503, detail="Email service quota reached. Try again later.")
        raise HTTPException(429, detail="Rate limit exceeded.")
    except ResendError as e:
        if int(e.code) in (401, 403):
            logger.error("Resend auth/config error: %s — %s", e.error_type, e.message)
            raise HTTPException(500, detail="Email service misconfigured.")
        raise HTTPException(500, detail=f"Email delivery failed: {e.message}")

# --- Routes ---
@app.post("/send")
@pay("$0.01")
def send_email(request: Request, body: EmailRequest):
    wallet = get_wallet_address(request)
    check_and_increment_wallet_limit(wallet)
    check_and_increment_domain_limit(wallet, str(body.to))
    result = _do_send(body)
    log_send_event(wallet, str(body.to), body.subject, result["id"])
    return {"message_id": result["id"]}

@app.get("/send/test")
@limiter.limit("100/hour")
async def send_test(request: Request):
    return {"message_id": "test_00000000-0000-0000-0000-000000000000"}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## State of the Art

### Resend SDK (2026)

- **Latest:** `resend` 2.23.0 (2026-02-23). v2.x is stable. The `>=2.0.0,<3.0.0` pin is appropriate.
- **No async client:** Issue #122 confirms this is a known gap with no ETA. The correct workaround is a plain `def` route (FastAPI runs it in a thread pool), not `run_in_threadpool` manually.
- **Automatic plain-text:** The server-side `text` auto-generation from `html` has been a stable Resend feature since it was announced in their changelog. It eliminates the need for any client-side HTML-to-text conversion library.
- **Python 3.7+** supported; no version concerns for Railway Python environments.

### FastAPI + x402 Pattern

The Phase 5–7 stack is fully established. Phase 8 adds no architectural novelty — it's the same FastAPI + fastapi-x402 + slowapi + per-wallet rate limit blueprint applied to a Resend HTTP integration.

### Railway Email Constraint

Railway Hobby plan blocks SMTP at the network level. Resend's HTTPS API is the only viable transactional email provider for Railway services at this tier. This is not a limitation for Phase 8 (already scoped to Resend), but it eliminates the entire class of SMTP-based alternatives.

---

## Open Questions

None blocking for Phase 8. The following are low-priority considerations:

1. **Resend free tier ceiling (100/day):** If legitimate usage spikes, upgrading to a paid Resend plan unblocks without code changes. No design action required now.
2. **In-memory rate limit persistence across restarts:** The stateless design is intentional and documented. If future requirements demand persistence across restarts, Redis could replace the dict — but this is a deferred concern (per CONTEXT.md).
3. **`reply_to` display-name format:** `EmailStr` rejects display-name format like `Name <email@domain.com>`. If callers reasonably expect to pass display-name format, consider stripping the name in a custom validator. Leave as-is for v1 — raw `EmailStr` is correct.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | One conflict resolved: INTEGRATION recommended `html2text` for plain-text fallback; PITFALLS confirmed Resend auto-generates `text` server-side. PITFALLS finding preferred per synthesis directive (SDK source + changelog inspected directly). `html2text` removed from stack and code examples. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples, State of the Art. Optional sections User Constraints, Phase Requirements, Open Questions also populated. |
| Dimension Coverage | PASS | INTEGRATION: SDK, code examples, error mapping, integration patterns — integrated. SECURITY: rate limiting, logging, email validation, abuse deterrence — integrated. PITFALLS: 10+ pitfalls, Don't Hand-Roll table — integrated. |
| Requirement Coverage | PASS | EMAIL-01 through EMAIL-05 all mapped to findings with specific implementation guidance and dimension citations. |

---

## Sources

### Primary (HIGH confidence)

- Resend Python SDK v2.23.0 source (`resend/http_client_requests.py`, `resend/exceptions.py`, `resend.Emails.SendParams`) — synchronous blocking behavior confirmed; exception hierarchy verified; TypedDict required keys inspected
- [Resend Send Email API Reference](https://resend.com/docs/api-reference/emails/send-email) — parameter list, `html`/`text` auto-generation behavior
- [Resend API Errors Reference](https://resend.com/docs/api-reference/errors) — full error type table with HTTP status codes
- [Resend Rate Limit Docs](https://resend.com/docs/api-reference/rate-limit) — 2 req/sec account-level; free tier 100/day, 3000/month
- [Resend Automatic Plain Text Emails Changelog](https://resend.com/changelog/automatic-plain-text-emails) — confirms server-side auto-generation; opt-out by setting `text: ""`
- [Resend FastAPI Guide](https://resend.com/docs/send-with-fastapi) — initialization + route handler pattern
- PyPI `resend` package — version 2.23.0 (2026-02-23), dependencies: `requests>=2.31.0`
- `/Users/jameswisdom/projects/x402-mcp-server/x402-search-api/main.py` — Phase 7 production implementation; per-wallet rate limit pattern, wallet extraction path, slowapi usage, logging setup
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/STATE.md` — accumulated decisions; per-wallet rate limit pattern formally recorded

### Secondary (MEDIUM confidence)

- [resend-python issue #122](https://github.com/resend/resend-python/issues/122) — async support gap confirmed by maintainers
- [resend-python issue #65](https://github.com/resend/resend-python/issues/65) — single bad address in `to` blocks entire send; confirmed expected behavior
- [resend-node issue #455](https://github.com/resend/resend-node/issues/455) — 403 validation error after UI shows domain verified (propagation delay)
- [Railway Outbound Networking Docs](https://docs.railway.com/reference/outbound-networking) — SMTP ports blocked on Hobby plan
- FastAPI async/sync documentation — plain `def` routes run in thread pool automatically
- Pydantic v2 documentation — `EmailStr` requires `email-validator` install via `pydantic[email]`
- RFC 5321 / RFC 5322 — 998-character subject line limit

### Tertiary (LOW confidence)

- Per-recipient domain limit recommendation (5/wallet/domain/day) — derived from threat model reasoning; validate against observed abuse patterns before treating as a hard requirement
- GitHub ecosystem search (`resend.Emails.send` in Python codebases) — confirmed sync-only pattern across khoj-ai, OpenHands, camel-ai, airweave-ai, phospho-app

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH (verified against PyPI, official docs, SDK source, GitHub examples)
- SECURITY: HIGH (Phase 7 source inspected directly; patterns verified in production code)
- PITFALLS: HIGH (SDK source-inspected; official changelog verified; GitHub issues cited)

**Research date:** 2026-03-14
**Valid until:** 2026-09 (Resend SDK v3.x release would require pin review; fastapi-x402 minor versions are backward-compatible)
**Dimensions researched:** INTEGRATION, SECURITY, PITFALLS
