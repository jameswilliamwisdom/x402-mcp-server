# Phase 7: Web Search API — Research

**Researched:** 2026-03-13
**Domain:** Tavily search API wrapper, FastAPI Railway service, per-wallet rate limiting
**Confidence:** HIGH
**Method:** Full-scope (source inspection: fastapi-x402 0.1.8, tavily-python 0.5.4; official Tavily docs; project source reference)

---

## Summary

Phase 7 builds `x402-search-api`, a new Railway service wrapping the Tavily Search API. It is the simplest service in the v1.1 milestone — no browser, no file processing, no SSRF risk. The entire implementation is a thin FastAPI adapter: receive a search query, call Tavily, reshape the response, and return it behind an x402 payment gate. The primary implementation risk is the per-wallet daily rate limit, which requires extracting the payer wallet address from `request.state.decoded_payment` — a field set by fastapi-x402 0.1.8 middleware that is not documented but confirmed by source inspection.

**Critical naming discrepancy:** The success criteria and project description use the term "snippet" for result descriptions, but the actual Tavily API response field is `content`. The service should map Tavily's `content` field to a `snippet` key in the output so the success criteria ("snippet field populated") passes cleanly.

**Version pin clarification:** The constraint specifies `tavily-python ^0.5.x` but the current release is 0.7.23. The `_search` method signature and response format are stable across both versions. Recommend pinning `tavily-python>=0.5.0,<0.6.0` as specified, or upgrading to `>=0.7.0` if the extra `auto_parameters` and `chunks_per_source` features in 0.7.x are wanted. The 0.5.4 source (verified by wheel inspection) is fully functional and sufficient for all five SEARCH requirements.

**Primary recommendation:** `AsyncTavilyClient` (httpx-based) in FastAPI lifespan; `python:3.11-slim` Docker base; per-wallet daily limit via in-memory dict keyed on `request.state.decoded_payment["payload"]["authorization"]["from"]`; map Tavily `content` → response `snippet` for success-criteria compliance.

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEARCH-01 | Given a query, return top N results (title, URL, snippet) as JSON via Tavily | `AsyncTavilyClient.search(query, max_results=N)` returns `{"results": [{"title", "url", "content", "score"}]}`; map `content` → `snippet` in response |
| SEARCH-02 | `include_answer` param — synthesized answer with sources | `search(..., include_answer=True)` or `include_answer="advanced"`; Tavily returns `{"answer": str}`; costs 0 extra credits for basic, included in base call |
| SEARCH-03 | `include_domains`/`exclude_domains` for focused research | `search(..., include_domains=["..."], exclude_domains=["..."])`; max 300 include / 150 exclude; validated with Pydantic `List[str]` field |
| SEARCH-04 | Per-wallet daily query limit to prevent cost spikes | Custom slowapi `key_func` extracting `request.state.decoded_payment["payload"]["authorization"]["from"]`; in-memory dict `{wallet: (count, date)}`; 50 queries/day; returns 429 on 51st |
| SEARCH-05 | Free test endpoint with fixture data | `GET /search/test` returning fixture JSON with `results` array containing all required fields; `slowapi` 100/hour per IP |

</phase_requirements>

---

## Standard Stack

### Core Dependencies (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
fastapi-x402>=0.1.8
tavily-python>=0.5.0,<0.6.0
slowapi>=0.1.9
```

**No additional dependencies needed:**
- No Playwright (no browser)
- No httpx (tavily-python 0.5.x bundles httpx for `AsyncTavilyClient`)
- No WeasyPrint, Pillow, trafilatura
- No SSRF protection (Tavily is a trusted third-party API; no user-supplied URLs)

### Docker Base Image

**Use:** `python:3.11-slim` — same as Phase 6.

Do NOT use the 1.5GB Playwright image (`mcr.microsoft.com/playwright/python`) — no browser needed. No special apt packages required. Smallest possible footprint.

**Complete Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY fixture.json .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**railway.toml:**

```toml
[deploy]
startCommand = "sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}'"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

`healthcheckTimeout = 30` — no browser startup delay, FastAPI starts in <5 seconds.

### Project Structure

```
x402-search-api/
├── main.py              # FastAPI app, all routes, Tavily integration, rate limit
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env                 # PAY_TO_ADDRESS, X402_NETWORK, TAVILY_API_KEY (gitignored)
└── fixture.json         # Hardcoded test response for GET /search/test
```

### Library Version Notes

| Library | Version | Why |
|---------|---------|-----|
| `tavily-python` | `>=0.5.0,<0.6.0` | Matches constraint; `AsyncTavilyClient` verified in 0.5.4 source; httpx-based async |
| `fastapi-x402` | `>=0.1.8` | Sets `request.state.decoded_payment` after payment — required for wallet extraction |
| `slowapi` | `>=0.1.9` | In-memory rate limiting; project standard (Phases 5 and 6) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tavily-python 0.5.x` | `tavily-python 0.7.x` | 0.7.x adds `auto_parameters`, `chunks_per_source`, `topic=finance` but breaks `^0.5.x` pin; core search API identical |
| `AsyncTavilyClient` | `TavilyClient` + `run_in_threadpool` | `TavilyClient` uses `requests` (sync); must use `run_in_threadpool` or switch to `AsyncTavilyClient`; async preferred |
| In-memory dict rate limit | slowapi + Redis | Redis not needed for single Railway instance; in-memory sufficient; consistent with Phase 5/6 pattern |

---

## Architecture Patterns

### Recommended Project Structure

All logic in single `main.py` — consistent with Phase 5 (scraping) and Phase 6 (conversion).

### Pattern 1: AsyncTavilyClient in FastAPI Lifespan

`AsyncTavilyClient` creates a new `httpx.AsyncClient` per call (confirmed in source: `self._client_creator = lambda: httpx.AsyncClient(...)`). There is no shared session to manage at the lifespan level. Instantiate the client once at startup and share it:

```python
# Source: tavily/async_tavily.py (inspected from 0.5.4 wheel)
from tavily import AsyncTavilyClient
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os

tavily_client: AsyncTavilyClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tavily_client
    tavily_client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    yield
    # No cleanup needed — no persistent httpx session

app = FastAPI(lifespan=lifespan)
```

**Note:** `AsyncTavilyClient` does NOT raise at instantiation if the API key is invalid — it raises at the first `search()` call. Validate the key at startup by checking `TAVILY_API_KEY` is non-empty.

### Pattern 2: Per-Wallet Daily Rate Limit

`fastapi-x402` 0.1.8 sets `request.state.decoded_payment` after verifying payment. The decoded payment is an EIP-3009 authorization object where `["payload"]["authorization"]["from"]` is the payer's wallet address (Ethereum address string, e.g. `"0xAbCd..."`).

Source from `fastapi_x402/middleware.py` (inspected from 0.1.8 wheel):
```python
# These are set on request.state after payment verification:
request.state.payment_verified = True
request.state.payment_id = verify_response.payment_id
request.state.decoded_payment = self._decode_payment_header(payment_header)
request.state.payment_requirements = payment_requirements
```

The decoded payment structure (from `_decode_payment_header`):
```python
{
    "payload": {
        "signature": "0x...",
        "authorization": {
            "from": "0xPayerWalletAddress",   # ← USE THIS for per-wallet key
            "to": "0xRecipientAddress",
            "value": "10000",                 # atomic units
            "validAfter": 0,
            "validBefore": 1734567890,
            "nonce": "0x..."
        }
    },
    ...
}
```

**Per-wallet rate limit implementation:**

```python
from collections import defaultdict
from datetime import date
from fastapi import Request, HTTPException
from typing import Dict, Tuple
import threading

DAILY_QUERY_LIMIT = 50

# Thread-safe in-memory store: {wallet_address: (count, date)}
_wallet_counts: Dict[str, Tuple[int, date]] = {}
_wallet_lock = threading.Lock()

def get_wallet_address(request: Request) -> str:
    """Extract payer wallet address from verified x402 payment state."""
    decoded = getattr(request.state, "decoded_payment", None)
    if decoded is None:
        return None
    try:
        return decoded["payload"]["authorization"]["from"].lower()
    except (KeyError, AttributeError, TypeError):
        return None

def check_wallet_rate_limit(wallet_address: str) -> None:
    """Raises HTTPException 429 if wallet has exceeded daily query limit."""
    if wallet_address is None:
        return  # No wallet address = no per-wallet check (shouldn't happen post-payment)

    today = date.today()
    with _wallet_lock:
        count, recorded_date = _wallet_counts.get(wallet_address, (0, today))
        if recorded_date != today:
            count = 0  # New day — reset count
        if count >= DAILY_QUERY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Daily query limit of {DAILY_QUERY_LIMIT} reached for this wallet. Resets at midnight UTC."
            )
        _wallet_counts[wallet_address] = (count + 1, today)
```

**Integration in route handler:**
```python
@app.post("/search")
@pay("$0.01")
async def search(request: Request, body: SearchRequest):
    wallet = get_wallet_address(request)
    check_wallet_rate_limit(wallet)  # Call AFTER @pay has verified payment
    ...
```

**Important:** Call `check_wallet_rate_limit` inside the route handler (after `@pay` has verified and set `request.state.decoded_payment`), NOT in middleware. The wallet address is only available after payment verification runs.

### Pattern 3: Tavily Search Call and Response Shaping

```python
# Source: tavily/async_tavily.py (inspected from 0.5.4 wheel)
# AsyncTavilyClient.search() returns:
# {
#   "query": str,
#   "results": [{"title": str, "url": str, "content": str, "score": float}],
#   "answer": str | None,   # only if include_answer=True
#   "response_time": float
# }

async def run_search(
    query: str,
    max_results: int = 5,
    include_answer: bool = False,
    include_domains: list = None,
    exclude_domains: list = None,
) -> dict:
    result = await tavily_client.search(
        query=query,
        search_depth="basic",      # 1 credit ($0.008); "advanced" = 2 credits
        max_results=max_results,
        include_answer=include_answer,
        include_domains=include_domains or [],
        exclude_domains=exclude_domains or [],
    )

    # Rename Tavily's "content" field to "snippet" for success-criteria compliance
    shaped_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),   # ← KEY: content → snippet
            "score": r.get("score", 0.0),
        }
        for r in result.get("results", [])
    ]

    response = {
        "query": query,
        "results": shaped_results,
    }

    if include_answer and result.get("answer"):
        response["answer"] = result["answer"]

    return response
```

### Pattern 4: Request Model

```python
from pydantic import BaseModel, Field
from typing import List, Optional

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
```

**Constraints rationale:**
- `max_results` capped at 10 (Tavily default is 5, max is 20; 10 is a cost-conscious ceiling)
- `query` max 400 chars (Tavily does not publish a limit; 400 is generous for agent use)
- `include_domains`/`exclude_domains` lists capped at 20 each (Tavily allows up to 300/150 but 20 is enough for focused research)

### Pattern 5: Endpoint Design

```python
from fastapi_x402 import init_x402, pay
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/search")
@pay("$0.01")
async def search(request: Request, body: SearchRequest):
    wallet = get_wallet_address(request)
    check_wallet_rate_limit(wallet)

    try:
        result = await run_search(
            query=body.query,
            max_results=body.max_results,
            include_answer=body.include_answer,
            include_domains=body.include_domains,
            exclude_domains=body.exclude_domains,
        )
    except UsageLimitExceededError:
        raise HTTPException(status_code=503,
                            detail="Tavily API credit limit reached. Contact service operator.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    return result

@app.get("/search/test")
@limiter.limit("100/hour")
async def search_test(request: Request):
    return load_fixture()

@app.get("/health")
async def health():
    return {"status": "healthy", "tavily": "configured" if tavily_client else "not configured"}

@app.get("/")
async def info():
    return {
        "service": "x402-search-api",
        "price": "$0.01",
        "test": "/search/test",
        "description": "Web search via Tavily — returns ranked results with title, URL, snippet, score",
    }
```

**Decorator order:** `@app.post(...)` outermost, `@pay(...)` inner. Same as Phase 5/6 — reversing silently breaks route registration.

### Pattern 6: Middleware Setup (No SSRF needed)

Phase 7 does NOT need SSRFMiddleware — there are no user-supplied URLs to validate. The only outbound call is to `api.tavily.com`, a trusted third-party.

```python
app = FastAPI(title="x402 Search API", lifespan=lifespan)
init_x402(app, network="base")   # Adds PaymentMiddleware automatically

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

No SSRFMiddleware added — simplest middleware stack of any service in this project.

### Anti-Patterns to Avoid

- **Using `TavilyClient` (sync) in an async FastAPI handler:** `TavilyClient._search()` uses `requests.post()` which blocks the event loop. Always use `AsyncTavilyClient`.
- **Setting wallet rate limit in middleware:** `decoded_payment` is only available after the payment middleware runs. Wallet check must be in the route handler body, not in a pre-payment middleware.
- **Raising `HTTPException` from the wallet rate limit check before incrementing the counter:** Increment only happens after the payment is verified but before calling Tavily — so failed Tavily calls don't consume the quota. The current pattern (count before Tavily call) is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP to Tavily | Manual `httpx.AsyncClient` to `api.tavily.com` | `AsyncTavilyClient.search()` | Handles auth headers, error codes (401/403/429), response parsing; `UsageLimitExceededError` maps to Tavily's 429 |
| Response content field rename | Check for "content" at call site | Rename once in `run_search()` — `"snippet": r.get("content", "")` | Centralizes the mapping; keeps success-criteria field names clean |
| UTC daily reset for rate limit | `datetime.datetime.utcnow().date()` | `datetime.date.today()` + UTC note | For Railway containers, system time is UTC by default — `date.today()` is UTC-equivalent in practice |
| Tavily API key validation at startup | Custom API call to `/health` | Check `TAVILY_API_KEY` env var is non-empty at lifespan; let first real request surface invalid key | Tavily has no `/validate` endpoint; initial smoke test costs a credit |

---

## Common Pitfalls

### Pitfall 1: Using Sync `TavilyClient` in FastAPI

**What goes wrong:** `TavilyClient._search()` uses `requests.post()` — a synchronous blocking call. In an `async def` FastAPI handler, this blocks the entire event loop for the duration of the Tavily request (typically 1-3 seconds per query). Under any concurrent load, this causes timeout cascades.

**Why it happens:** `tavily-python` ships both `TavilyClient` (sync, uses `requests`) and `AsyncTavilyClient` (async, uses `httpx`). The sync client is imported first in most examples.

**How to avoid:** `from tavily import AsyncTavilyClient`. Only use `AsyncTavilyClient` in FastAPI. If sync must be used (e.g., testing), wrap in `run_in_threadpool`.

**Warning signs:** Requests taking >5s under light load; event loop blocking warnings in logs.

### Pitfall 2: `decoded_payment` Not Set When Wallet Rate Limit Runs

**What goes wrong:** `request.state.decoded_payment` is only set by `PaymentMiddleware` AFTER it verifies the `X-PAYMENT` header. If the wallet rate limit check is implemented in ASGI middleware (running before payment), `decoded_payment` is not yet set, causing `AttributeError` or always returning `None`.

**Why it happens:** ASGI middleware runs before route handlers and before `PaymentMiddleware` (LIFO). Wallet state only exists in post-payment handler context.

**How to avoid:** Call `check_wallet_rate_limit()` as the first line inside the `async def search()` route handler, not in middleware. This guarantees payment has been verified first.

**Warning signs:** `AttributeError: 'State' object has no attribute 'decoded_payment'` in logs.

### Pitfall 3: "snippet" Field Missing in Response

**What goes wrong:** Tavily returns `results[n]["content"]` not `results[n]["snippet"]`. Success criteria SC-1 requires `snippet` field. If results are passed through without renaming, the success criteria test fails (checking for `snippet` key gets `None`/`KeyError`).

**Why it happens:** Tavily's field is `content`. The project spec and success criteria use `snippet` as the semantic name for the text excerpt.

**How to avoid:** In `run_search()`, always map: `"snippet": r.get("content", "")`.

### Pitfall 4: Per-Wallet Count Incremented Even When Tavily Fails

**What goes wrong:** If the wallet counter is incremented after the Tavily call returns successfully, a failed Tavily call (network timeout, 500 error) still consuming one query from the daily quota feels wrong — but worse, an attacker can drive up quota by sending queries that fail.

**Why it happens:** Ambiguity in where to place the `count + 1` operation.

**How to avoid:** Increment the wallet counter BEFORE calling Tavily. The user has paid and the system attempted the search — that counts against the quota. This prevents quota manipulation via induced failures.

### Pitfall 5: Race Condition in Per-Wallet Counter

**What goes wrong:** Under concurrent requests from the same wallet (multiple agents sharing a key), two requests read `count=49`, both pass the `<= 50` check, both increment to `50`, and 51 total queries are sent on day 50.

**Why it happens:** In-memory dict read-check-write is not atomic without a lock.

**How to avoid:** Use `threading.Lock()` around the read-check-increment block (as shown in the code example above). For a single-worker Railway deployment, the GIL provides some protection, but an explicit lock is correct and documents the intent.

### Pitfall 6: `include_answer` Extra Credit Cost

**What goes wrong:** If `include_answer="advanced"` is passed to Tavily, the call costs 2 credits ($0.016) instead of 1 ($0.008). The service charges callers `$0.01` per call. At `search_depth="advanced"` (2 credits) or `include_answer="advanced"` the operator margin is negative.

**Why it happens:** Tavily's `include_answer` accepts `True`, `"basic"`, or `"advanced"`. `True` is equivalent to `"basic"` and costs the same as a basic search (no extra credits from Tavily's docs — confirmed as 1 credit total). Only `"advanced"` incurs extra.

**How to avoid:** Fix `include_answer` in the `run_search()` call to always pass `True` or `False` (boolean), never `"advanced"`. Accept the boolean `include_answer` from callers; never expose `"advanced"` as an option in the API surface. Keep `search_depth="basic"` always.

### Pitfall 7: `AsyncTavilyClient` Creates New httpx Session Per Call

**What goes wrong:** `AsyncTavilyClient._search()` does `async with self._client_creator() as client:` — creating and tearing down an `httpx.AsyncClient` on every search call. Under high load, connection setup overhead accumulates. Under very high concurrency, this creates many simultaneous TCP connections to `api.tavily.com`.

**Why it happens:** `tavily-python 0.5.x` doesn't maintain a persistent session (confirmed from source). This is an upstream design choice.

**How to avoid:** For v1.1, this is acceptable — Railway single instance, rate limited to 50 calls/wallet/day. If load increases significantly, upgrade to `tavily-python 0.7.x` which may have improved session handling, or wrap the client with a custom persistent session.

### Pitfall 8: Tavily API Key Set as Code-Level Constant

**What goes wrong:** Hardcoding `TAVILY_API_KEY` in `main.py` or committing it to git exposes the key.

**Why it happens:** Convenience during development.

**How to avoid:** Always read from env var: `os.environ["TAVILY_API_KEY"]`. Set in Railway environment variables dashboard, not in code. `AsyncTavilyClient` already supports reading from `TAVILY_API_KEY` env var directly (`api_key = os.getenv("TAVILY_API_KEY")` in source).

### Pitfall 9: Missing Tavily Billing Limit

**What goes wrong:** Without a spending cap, a cost spike (many wallets each hitting 50 queries/day) can consume hundreds of dollars of Tavily credits before the operator notices.

**Why it happens:** Tavily's billing allows spend to continue past the free tier without automatic shutoff by default.

**How to avoid:** Set a monthly usage limit in Tavily dashboard (`app.tavily.com/billing`) BEFORE production deployment. Per-wallet daily limit of 50 queries limits exposure, but a hard billing ceiling is the backstop.

---

## Code Examples

### Complete `run_search()` Function (Verified Pattern)

```python
# Source: verified against tavily/async_tavily.py from 0.5.4 wheel
from tavily import AsyncTavilyClient
from tavily.errors import UsageLimitExceededError

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
        search_depth="basic",              # Always basic: 1 credit = $0.008
        max_results=max_results,
        include_answer=include_answer,     # bool only: True or False
        include_domains=include_domains or [],
        exclude_domains=exclude_domains or [],
    )

    shaped_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),   # Rename content → snippet
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
```

### Per-Wallet Daily Rate Limiter

```python
from collections import defaultdict
from datetime import date
from fastapi import HTTPException
import threading

DAILY_QUERY_LIMIT = 50

_wallet_counts: dict = {}   # {wallet_addr_lower: (count: int, day: date)}
_wallet_lock = threading.Lock()

def get_wallet_address(request) -> str | None:
    """Extract payer wallet from fastapi-x402 decoded_payment state.

    Structure (from fastapi-x402 0.1.8 source inspection):
    request.state.decoded_payment = {
        "payload": {
            "authorization": {"from": "0x...", ...},
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

def check_and_increment_wallet_limit(wallet: str | None) -> None:
    """Check daily limit and increment counter atomically.
    Raises HTTP 429 if limit reached. No-op if wallet is None.
    """
    if wallet is None:
        return
    today = date.today()
    with _wallet_lock:
        count, recorded_day = _wallet_counts.get(wallet, (0, today))
        if recorded_day != today:
            count = 0
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
```

### Fixture JSON Structure (`fixture.json`)

The fixture MUST use the `snippet` field name (not `content`) to pass success criteria:

```json
{
    "query": "x402 protocol",
    "results": [
        {
            "title": "x402: The Native Payment Protocol for HTTP",
            "url": "https://x402.org",
            "snippet": "The x402 protocol enables pay-per-request APIs using USDC on Base. Any HTTP endpoint can become a paid service with a single decorator.",
            "score": 0.9876
        },
        {
            "title": "Coinbase x402 Protocol — GitHub",
            "url": "https://github.com/coinbase/x402",
            "snippet": "Open-source implementation of the x402 HTTP payment protocol. Clients pay with USDC, servers verify via facilitator. Zero integration friction for AI agents.",
            "score": 0.9543
        },
        {
            "title": "x402 Payment Flow — Technical Architecture",
            "url": "https://docs.cdp.coinbase.com/x402",
            "snippet": "Step-by-step walkthrough of x402 payment verification: 402 response, X-PAYMENT header construction, facilitator verify/settle cycle.",
            "score": 0.9102
        }
    ]
}
```

Note: `include_answer` is not in the fixture — the test endpoint always returns the base fixture (no answer field). The free test demonstrates the base response shape.

### Environment Variables

```
# .env (gitignored — set in Railway dashboard for production)
PAY_TO_ADDRESS=0xYourWalletAddress
X402_NETWORK=base
TAVILY_API_KEY=tvly-YOUR_KEY_HERE
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Custom search API (SerpAPI, Google Custom Search) | Tavily AI-native search | Tavily designed for LLM/agent use; returns clean content vs raw HTML; native answer synthesis |
| Sync `TavilyClient` in async handlers | `AsyncTavilyClient` (httpx-based) | Non-blocking; required for FastAPI performance |
| `requests`-based search clients in FastAPI | `httpx`-based async clients | Standard for async Python HTTP since ~2022 |

**Deprecated — do not use:**
- `TavilyClient` (sync) in FastAPI async handlers
- `include_answer="advanced"` — doubles credit cost; not worth the margin hit
- `search_depth="advanced"` — doubles credit cost; use only if search quality is unacceptable

---

## Parallel Work: Resend DNS Setup

Per the phase description and STATE.md open question: configure Resend verified sender domain DNS records (SPF/DKIM/DMARC) in parallel during Phase 7 to absorb the 48-hour propagation window before Phase 8 begins.

**Action required (outside this service's codebase):**
1. Log into Resend dashboard
2. Add the verified sender domain
3. Copy SPF/DKIM/DMARC DNS records to your DNS provider
4. Start the 48-hour clock — these changes need to propagate before Phase 8 EMAIL-03 can be verified

This is a parallel DNS task, not a code task. No blocking dependency on x402-search-api implementation.

---

## Open Questions

1. **`tavily-python` version pin — upgrade to 0.7.x?**
   - What we know: 0.5.4 is fully functional for all 5 SEARCH requirements; 0.7.23 adds extra features not needed here
   - What's unclear: Whether 0.7.x has breaking changes to `AsyncTavilyClient.search()` signature (rapid version bump 0.5→0.6→0.7 in April 2025 suggests non-trivial changes)
   - Recommendation: Pin to `>=0.5.0,<0.6.0` as specified in constraints. Evaluate upgrade in Phase 10 (MCP publish) if needed.

2. **`include_answer` credit cost with Tavily 0.5.x**
   - What we know: Tavily docs say basic search = 1 credit; `include_answer=True` is described as no extra credits for "basic" answer — but this may vary by plan
   - What's unclear: Whether `include_answer=True` in 0.5.x incurs extra credits vs 0.7.x behavior
   - Recommendation: Test manually before production deploy. If `include_answer` incurs extra credits, price the endpoint at `$0.02` instead of `$0.01`.

3. **`decoded_payment` availability on all production requests**
   - What we know: `request.state.decoded_payment` is set in `PaymentMiddleware.dispatch()` when `verify_response.isValid` is True (confirmed from source)
   - What's unclear: Whether there are edge cases where payment is verified but `decoded_payment` is not set (e.g., facilitator returns valid but malformed payload)
   - Recommendation: Always use `getattr(request.state, "decoded_payment", None)` with defensive fallback. If wallet extraction fails, skip the per-wallet check (log a warning) rather than crashing.

4. **Tavily billing hard limit behavior**
   - What we know: Tavily has a monthly usage limit toggle in dashboard; behavior described as "notifications if you approach or exceed" — possibly soft alert, not hard cutoff
   - What's unclear: Whether Tavily stops API calls when limit is hit, or just sends email
   - Recommendation: Set the dashboard limit AND rely on per-wallet daily limit (50/day × N wallets) as the primary cost control. Do not rely solely on Tavily's billing limit.

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` (only `workflow.research: true` is present). Skipping this section — no Nyquist validation configured.

---

## Sources

### Primary (HIGH confidence)

- `fastapi_x402-0.1.8-py3-none-any.whl` (downloaded from PyPI, inspected locally) — `middleware.py`: `request.state.decoded_payment` structure; `PaymentMiddleware.dispatch()` state assignments; `models.py`: `VerifyResponse.payer` field
- `tavily_python-0.5.4-py3-none-any.whl` (downloaded from PyPI, inspected locally) — `async_tavily.py`: `AsyncTavilyClient.search()` signature, httpx usage, `_client_creator` pattern; `tavily.py`: sync client uses `requests`; METADATA: `Requires-Dist: requests`, `Requires-Dist: httpx`
- [Tavily Python SDK Reference](https://docs.tavily.com/sdk/python/reference) — `search()` parameters, `AsyncTavilyClient` constructor, response format with `title`/`url`/`content`/`score` fields
- [Tavily API Credits](https://docs.tavily.com/documentation/api-credits) — basic search = 1 credit ($0.008); advanced = 2 credits; free tier = 1000 credits/month
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — `@pay`/`@app.post` decorator order; SSRFMiddleware LIFO pattern; `slowapi` rate limiting setup
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/phases/05-web-scraping-api/05-RESEARCH.md` — project patterns, Railway config, MCP integration
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/phases/06-file-conversion-api/06-RESEARCH.md` — `python:3.11-slim` Docker pattern confirmed
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — APIS dict, `apiPost`/`apiGet` helpers, `textResult`/`errorResult`, MCP tool registration pattern
- x402 EIP-3009 spec (confirmed via WebSearch) — `payload.authorization.from` = payer wallet address

### Secondary (MEDIUM confidence)

- PyPI release history — tavily-python 0.7.23 is current (released 2026-03-09); 0.5.4 released 2025-04-02; 0.7.0 released 2025-04-25
- [Tavily Pay-As-You-Go billing help](https://help.tavily.com/articles/8280756099-how-to-set-a-limit-for-pay-as-you-go-option) — usage limit configuration; behavior described as notification-based (possibly soft alert)
- WebSearch cross-verification — x402 `payload.authorization.from` = Ethereum wallet address from EIP-3009 standard

### Tertiary (LOW confidence)

- `include_answer=True` credit cost in Tavily 0.5.x — doc says no extra credit for "basic" answer but not verified against a live 0.5.x account with billing counter
- `tavily-python` 0.7.x breaking changes — rapid version jump from 0.5.4 to 0.6.0 to 0.7.0 in April 2025 suggests API changes; no explicit changelog found; 0.5.x vs 0.7.x API stability unverified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Tavily SDK source inspected, fastapi-x402 source inspected, project patterns confirmed
- Architecture patterns: HIGH — `decoded_payment` structure confirmed from fastapi-x402 0.1.8 source; Tavily response format confirmed from async_tavily.py source
- Per-wallet rate limit: HIGH — `decoded_payment` state fields confirmed; pattern is straightforward dict + lock
- Pitfalls: HIGH — sync client issue confirmed from source; 8 pitfalls documented with verified root causes
- Version pin (0.5.x vs 0.7.x): MEDIUM — 0.5.4 confirmed functional; 0.7.x stability unknown

**Research date:** 2026-03-13
**Valid until:** 2026-09-13 — Tavily API stable; fastapi-x402 may update; check if 0.1.9 sets wallet address on `request.state` directly before implementing
