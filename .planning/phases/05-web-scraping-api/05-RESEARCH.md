# Phase 5: Web Scraping API - Research

**Researched:** 2026-03-12
**Domain:** Python web scraping, Playwright headless browser, FastAPI, Railway deployment, SSRF protection
**Confidence:** HIGH
**Method:** MECE decomposition (4 dimensions: STACK, INTEGRATION, SECURITY, PITFALLS)

---

## Summary

Phase 5 builds a new Railway service (`x402-scraping-api`) that accepts a URL via POST and returns structured JSON — markdown-converted main content, links, tables, images, and page metadata. JS-rendered pages are supported via Playwright's persistent browser pattern. The service integrates with the existing MCP server via the standard APIS dict + `server.tool()` pattern.

The technology choices are well-determined: `trafilatura` 2.0 for content extraction and markdown conversion (outperforms all alternatives in benchmarks, extracts metadata in one call), `beautifulsoup4` + `lxml` for structured link/image/table extraction from raw HTML, and `pandas.read_html()` for table extraction with correct rowspan/colspan handling. The Docker base image is `mcr.microsoft.com/playwright/python:v1.44.0-jammy` — this eliminates the 30+ `apt-get` dependency layer required by the existing screenshot-api approach and is confirmed as the current standard for Playwright in Docker.

SSRF protection requires two layers: a pre-flight `validate_url_for_ssrf()` function using `socket.getaddrinfo()` (not `gethostbyname()` — required for IPv6 coverage) that checks all resolved addresses, and a Playwright route-level intercept that aborts document navigations to private IPs (to catch redirect-chain SSRF). The SSRF check must run in ASGI middleware added after `init_x402()` so it fires before the x402 payment middleware in the LIFO execution order. The key cross-cutting risk is the timeout budget: Playwright's per-action timeouts are independent — a shared 8-second ceiling requires `asyncio.wait_for()` as an outer guard, not independent `timeout=8000` on each call.

**Primary recommendation:** Use `mcr.microsoft.com/playwright/python:v1.44.0-jammy` as base image, `trafilatura` + `beautifulsoup4` + `pandas` for extraction, stdlib `socket`/`ipaddress` + Playwright route intercept for SSRF, `SSRFMiddleware` added after `init_x402()` for correct middleware ordering. Validate the Docker build locally before Railway deploy.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### Response Shape
- Full extraction: markdown text, links array, tables array, images array (src + alt), metadata object
- Main content only — strip nav, footer, sidebar, ads before markdown conversion
- Links as flat array of `{url, text}` objects, all resolved to absolute URLs
- No screenshot in response — separate screenshot API already exists
- Include HTTP status code and curated response headers (content-type, content-language, x-robots-tag) in metadata
- Include `final_url` in response (may differ from input URL after redirects)

### Error Handling
- Blocked sites (Cloudflare, CAPTCHA, 403): return 200 with `{success: false, error: "blocked_by_protection", detail: "..."}`
- Empty/login-wall pages: return partial extraction with `{warning: "no_content_extracted"}`
- Timeouts: return whatever was extracted before timeout with `{warning: "timeout"}`
- Non-HTML content types: reject with clear error (PDF, images, etc. — use other x402 APIs)
- HTML pages only — no best-effort handling of other formats
- Follow up to 5 redirects automatically; include `final_url` in response
- SSRF-blocked requests (private IPs): return 400 error, no charge to caller

### User-Agent & Browser
- Default Chrome desktop User-Agent, not configurable by caller
- No mobile or custom UA override — keeps API surface simple

### Free Test Endpoint
- Separate `/scrape/test` GET route (not the same endpoint with a magic URL)
- Full demo fixture: all fields populated (markdown, links, tables, images, metadata)
- Fixture content: x402 protocol documentation page (on-brand, self-referential)
- Light rate limit: 100 requests/hour per IP

### Pricing & Limits
- $0.02 USDC per scrape (covers heavier Playwright/Chromium compute)
- 8-second Playwright timeout ceiling (page load + wait_for combined)
- 5MB response size cap (truncate markdown if exceeded)

### Claude's Discretion
- Per-wallet rate limit on paid scrapes (pick a reasonable number that prevents abuse without limiting research agents)
- Content extraction library choice (readability, cheerio, mozilla readability, etc.)
- Exact response JSON field naming conventions
- Loading/navigation strategy within Playwright (networkidle vs domcontentloaded)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRAPE-01 | Given a URL, return structured JSON with markdown text, extracted links, and page metadata | `trafilatura.extract()` for markdown + metadata; `beautifulsoup4` for links array; `ScrapeResponse` schema in DIM-INTEGRATION; `trafilatura.extract_metadata()` for title, description, og fields |
| SCRAPE-02 | JS-rendered pages supported via Playwright (not just static HTML) | Persistent browser pattern (DIM-STACK); `async_playwright` + `browser.new_context()` per request; `page.content()` returns post-JS DOM; `wait_until="domcontentloaded"` confirmed correct strategy |
| SCRAPE-03 | `wait_for` CSS selector parameter for async SPA content | `page.wait_for_selector(wait_for, timeout=...)` within the shared 8-second budget via `asyncio.wait_for()` guard (DIM-STACK, DIM-PITFALLS); `ScrapeRequest.wait_for: Optional[str]` field |
| SCRAPE-04 | SSRF protection — server-side IP validation rejects private/loopback ranges | `validate_url_for_ssrf()` with `socket.getaddrinfo()` + `ipaddress` stdlib (DIM-SECURITY); `SSRFMiddleware` added after `init_x402()` for pre-payment execution (DIM-SECURITY, DIM-INTEGRATION); Playwright `page.route()` document-level intercept for redirect-chain protection |
| SCRAPE-05 | Free test endpoint with fixture data (no live scraping) | `GET /scrape/test` route returning `fixture.json` (DIM-INTEGRATION); `slowapi` rate limiter at 100 req/hr per IP; fixture demonstrates full `ScrapeResponse` schema with x402.org content |

</phase_requirements>

---

## Standard Stack

### Core Dependencies (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
playwright>=1.44.0
fastapi-x402>=0.1.8
trafilatura>=2.0.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
slowapi>=0.1.9
pandas>=2.0.0
```

**pandas** is added beyond the baseline STACK recommendation to handle rowspan/colspan table extraction correctly (DIM-PITFALLS). At ~20MB, it is negligible against the 1.5-2GB Playwright base image.

### Docker Base Image

**Use:** `mcr.microsoft.com/playwright/python:v1.44.0-jammy`

- Ubuntu 22.04 LTS, Python 3.10
- Playwright 1.44.0 pre-installed with Chromium 125.0.6422.14 and all system dependencies
- Eliminates 30+ `apt-get` packages and `playwright install` step required by the existing `python:3.11-slim` approach
- Validate with local `docker build` before Railway deploy — this is the highest-risk unknown in the phase

### Library Rationale

| Library | Chosen Over | Reason |
|---------|-------------|--------|
| `trafilatura` 2.0 | `readability-lxml`, `newspaper3k` | Best benchmark scores; native markdown output; metadata extraction in same library; `newspaper3k` unmaintained since 2022 |
| `beautifulsoup4` + `lxml` | `parsel` | Standard in project ecosystem; `lxml` already a `trafilatura` dependency; BS4 for link/image extraction on raw HTML (trafilatura's `include_links` is experimental) |
| `pandas.read_html()` | Custom BS4 table iterator | Handles rowspan/colspan correctly; `lxml` backend already present; naive BS4 iteration produces garbled data on merged-cell tables |
| `slowapi` | `fastapi-limiter` (Redis-backed) | In-memory sufficient for single Railway instance; no Redis dependency |
| `async_playwright` | `selenium`, `nodriver`, `sync_playwright` | First-class async API required by FastAPI; official Docker images; persistent browser pattern; `sync_playwright` raises `NotImplementedError` in async context |
| `wait_until="domcontentloaded"` | `"networkidle"` | `networkidle` officially discouraged by Playwright — pages with analytics/chat widgets never settle; `domcontentloaded` is fast and reliable |

### Project File Structure

```
x402-scraping-api/
├── main.py              # FastAPI app, lifespan, all routes, extraction logic
├── requirements.txt     # Python dependencies
├── Dockerfile           # FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
├── railway.toml         # Health check, restart policy, start command
├── .env                 # PAY_TO_ADDRESS, X402_NETWORK (gitignored)
└── fixture.json         # Hardcoded test response for /scrape/test
```

Single-file `main.py` pattern consistent with existing `screenshot-api` and `pdf-api` services.

---

## Architecture Patterns

### Persistent Browser + Per-Request Context

One `Browser` instance lives for the process lifetime (launched in FastAPI lifespan). Each request gets its own `BrowserContext`, closed in `finally`.

```python
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser
from typing import Optional

browser: Optional[Browser] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global browser
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]
    )

    # Register crash handler — sets browser to None so health check surfaces it
    def on_browser_disconnect():
        global browser
        browser = None
        logger.error("Playwright browser disconnected — Railway will restart container")

    browser.on("disconnected", on_browser_disconnect)
    yield
    if browser:
        await browser.close()
```

### Per-Request Scrape Function with Shared Timeout Budget

The 8-second ceiling applies to the combined `page.goto()` + `wait_for_selector()` sequence. Use a monotonic start time to allocate remaining budget to each Playwright call.

```python
import asyncio
import time

async def scrape_page(url: str, wait_for: Optional[str]) -> dict:
    TOTAL_BUDGET_S = 8.0
    start = time.monotonic()

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        permissions=[],
        service_workers="block",
    )
    # Route blocking at CONTEXT level (not page level — avoids memory leak)
    await context.route("**/*", handle_route)

    try:
        page = await context.new_page()

        # Abort document-level navigations to private IPs (redirect-chain SSRF)
        await context.route("**/*", abort_private_navigation)

        elapsed = time.monotonic() - start
        goto_timeout = max(1000, int((TOTAL_BUDGET_S - elapsed) * 1000))
        response = await page.goto(url, wait_until="domcontentloaded", timeout=goto_timeout)

        status_code = response.status if response else None

        if wait_for:
            elapsed = time.monotonic() - start
            selector_timeout = max(500, int((TOTAL_BUDGET_S - elapsed) * 1000))
            await page.wait_for_selector(wait_for, timeout=selector_timeout)

        html = await page.content()
        final_url = page.url

        # Guard against data: / blob: final_url
        if final_url.startswith(("data:", "blob:")):
            final_url = url
            # caller adds "navigation_to_non_http_url" to warnings

        return {"html": html, "final_url": final_url, "status_code": status_code}
    finally:
        await context.close()  # Close CONTEXT, never browser
```

### Content Extraction Pipeline

```python
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
from io import StringIO

def extract_content(html: str, page_url: str) -> dict:
    warnings = []

    # 1. Main content → markdown (trafilatura)
    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=False,    # Experimental — use BS4 instead
        include_tables=False,   # Handled by pandas below
        url=page_url,
        no_fallback=False,
    )

    if markdown is None:
        warnings.append("no_content_extracted")
    elif len(markdown.encode("utf-8")) > 5_000_000:
        # Truncate by bytes (not characters) to handle multi-byte Unicode correctly
        encoded = markdown.encode("utf-8")
        markdown = encoded[:5_000_000].decode("utf-8", errors="ignore")
        warnings.append("truncated")

    # 2. Metadata (trafilatura)
    meta = trafilatura.extract_metadata(html, default_url=page_url)
    metadata = {
        "title": meta.title if meta else None,
        "description": meta.description if meta else None,
        "og_title": meta.og_title if meta and hasattr(meta, "og_title") else None,
        "og_image": meta.image if meta else None,
        "canonical_url": meta.url if meta else None,
        "language": meta.language if meta else None,
    }

    # 3. Links — BS4 on raw HTML (not trafilatura output — experimental there)
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        links.append({"url": urljoin(page_url, href), "text": tag.get_text(strip=True)})

    # 4. Images — BS4 on raw HTML
    images = []
    for tag in soup.find_all("img", src=True):
        images.append({
            "src": urljoin(page_url, tag.get("src", "")),
            "alt": tag.get("alt", ""),
        })

    # 5. Tables — pandas (handles rowspan/colspan correctly)
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
        pass  # No tables found

    return {
        "markdown": markdown,
        "links": links,
        "images": images,
        "tables": tables,
        "metadata": metadata,
        "warnings": warnings,
    }
```

### Endpoint Design

```python
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi_x402 import init_x402, pay
from pydantic import BaseModel, Field
from typing import Annotated, Optional
from pydantic_core import Url
from pydantic import UrlConstraints

BoundedHttpUrl = Annotated[
    Url,
    UrlConstraints(allowed_schemes=["http", "https"], max_length=2048)
]

class ScrapeRequest(BaseModel):
    url: BoundedHttpUrl = Field(..., description="URL to scrape (must be http/https)")
    wait_for: Optional[str] = Field(None, max_length=500,
        description="CSS selector to wait for before extracting (SPA support)")

@app.post("/scrape")          # Outermost — route registration
@pay("$0.02")                 # Inner — payment gate
async def scrape(request: Request, body: ScrapeRequest):
    if browser is None or not browser.is_connected():
        raise HTTPException(status_code=503, detail="Browser unavailable — container restarting")
    ...

@app.get("/scrape/test")
@limiter.limit("100/hour")
async def scrape_test(request: Request):
    return load_fixture()

@app.get("/health")
async def health():
    # Always returns HTTP 200 — Railway checks status code only, not body
    return {"status": "healthy", "browser": browser is not None and browser.is_connected()}

@app.get("/")
async def info():
    return {"service": "x402-scraping-api", "price": "$0.02", "test": "/scrape/test"}
```

**Decorator order is critical:** `@app.post(...)` must be outermost, `@pay(...)` inner. Reversing silently breaks route registration.

### SSRF Middleware (Pre-Payment)

ASGI middleware execution order is LIFO. Add SSRF middleware AFTER `init_x402()` so it executes FIRST.

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json

class SSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path == "/scrape":
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                url = body.get("url", "")
                if url:
                    validate_url_for_ssrf(str(url))
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"SSRF validation failed: {e}"}
                )
            except (json.JSONDecodeError, Exception):
                pass  # Let Pydantic validation handle malformed bodies
        return await call_next(request)

app = FastAPI(lifespan=lifespan)
init_x402(app, network="base")    # Added first → runs LAST (LIFO)
app.add_middleware(SSRFMiddleware) # Added second → runs FIRST (LIFO)
```

### Railway Configuration

**Dockerfile:**
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY fixture.json .

EXPOSE 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

CMD is shell form (not exec form) — required for `${PORT}` variable expansion. `--host 0.0.0.0` is required (not `::`) for Railway's IPv4 proxy.

**railway.toml:**
```toml
[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
healthcheckPath = "/health"
healthcheckTimeout = 120
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

`healthcheckTimeout = 120`: Playwright browser takes ~10-15 seconds to initialize. Without this, Railway restarts the container before it is ready.

### MCP Server Integration

```typescript
// In src/index.ts APIS dict
scrape: {
  name: "Web Scraping API",
  baseUrl: "https://x402-scraping-api-production.up.railway.app", // fill after deploy
  price: "$0.02",
  description: "Scrape any URL and return structured JSON: markdown text, links, tables, images, metadata",
  usesX402: true,
},

// Tool registration
server.tool(
  "x402_scrape",
  `Scrape a URL and return structured content as JSON.
Price: $0.02 USDC per scrape | Free test: returns fixture data only.
Returns: markdown (main content, nav/ads stripped), links [{url, text}], tables [{headers, rows}],
images [{src, alt}], metadata (title, description, og_title, og_image, canonical_url, language,
status_code, content-type, content-language, x-robots-tag), final_url, warnings.
Without X402_PRIVATE_KEY, only /scrape/test fixture endpoint is available.`,
  {
    url: z.string().url().describe("URL to scrape (must be http/https)"),
    wait_for: z.string().max(500).optional()
      .describe("CSS selector to wait for before extracting — for SPAs (e.g., '.article-body')"),
  },
  async (params) => {
    const base = APIS.scrape.baseUrl;
    try {
      if (PRIVATE_KEY) {
        const data = await apiPost(base, "/scrape",
          { url: params.url, ...(params.wait_for ? { wait_for: params.wait_for } : {}) },
          true
        );
        return textResult({ mode: "paid", cost: "$0.02", ...data });
      } else {
        const data = await apiGet(base, "/scrape/test");
        return textResult({ mode: "free_test",
          note: "Free test — fixture data only. Set X402_PRIVATE_KEY for live scraping.", ...data });
      }
    } catch (err: any) { return errorResult(err.message); }
  }
);
```

Paid mode uses `apiPost` (JSON body to `POST /scrape`). Free mode uses `apiGet` (no body to `GET /scrape/test`). These are different HTTP methods by design — do not use `apiGet` for the paid endpoint.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Source |
|---------|-------------|-------------|--------|
| Table extraction with rowspan/colspan | Custom BS4 cell-tracking matrix | `pandas.read_html()` | DIM-PITFALLS |
| Per-request total timeout budget | Individual `timeout=8000` on each Playwright call | `asyncio.wait_for(coro, timeout=8.0)` or shared-budget pattern | DIM-PITFALLS |
| Markdown byte-length truncation | Character-count check (`len(markdown) > 5_000_000`) | `encoded = text.encode("utf-8"); encoded[:5_000_000].decode("utf-8", errors="ignore")` | DIM-PITFALLS |
| Cloudflare/block detection | Custom fingerprint analysis, browser stealth | HTTP status check + `"Just a moment"` / `"cf-browser-verification"` HTML string check | DIM-PITFALLS |
| Browser crash recovery | Auto-reconnect to crashed Playwright browser | `browser.on("disconnected", ...)` sets global to `None`; Railway `ON_FAILURE` restart policy recovers | DIM-PITFALLS |
| SSRF redirect-chain protection (non-Playwright HTTP) | Custom redirect-intercepting `requests` wrapper | `drawbridge` (pip) — only if adding non-Playwright HTTP fetches | DIM-SECURITY |
| SSRF IP range validation | Custom regex or CIDR math | Python stdlib `ipaddress` module | DIM-SECURITY |
| IPv6-aware DNS resolution | `socket.gethostbyname()` (IPv4-only) | `socket.getaddrinfo(hostname, None)` — resolves both A and AAAA records | DIM-SECURITY |

---

## Common Pitfalls

### Browser Lifecycle

**Context not closed on exception** (STACK): Always wrap per-request logic in `try/finally`. Close `context`, never `browser`. The `browser` is global and lives for the process lifetime. Closing it per-request crashes all subsequent requests.

**Browser crash leaves service appearing healthy** (PITFALLS): After a Playwright `Browser` disconnects, it cannot be reconnected. Register `browser.on("disconnected", ...)` to set the global to `None`. Check `browser is None or not browser.is_connected()` at the start of every request handler and return HTTP 503. Railway's `ON_FAILURE` restart policy handles recovery.

**`sync_playwright` inside FastAPI raises `NotImplementedError`** (PITFALLS): FastAPI runs on asyncio. `sync_playwright()` creates a new event loop and raises `NotImplementedError: This event loop is already running`. Always use `async_playwright()`.

**`uvicorn --reload` breaks Playwright lifespan** (PITFALLS): `--reload` uses a subprocess model; the global `browser` variable is not shared between reloader and worker processes. Do not use `--reload` with this service. Restart manually during development.

### Timeout Management

**Timeout cascade — goto() and wait_for_selector() do NOT share the 8-second budget** (PITFALLS): Playwright timeouts are per-action. Two 8-second timeouts = 16 seconds worst case. Use a shared monotonic start time to allocate remaining budget to each call, or wrap the entire operation in `asyncio.wait_for(..., timeout=8.0)`.

### Content Extraction

**`trafilatura.extract()` returns `None`, not empty string, on failure** (STACK): Always check `if markdown is None` before string operations. Return `{warning: "no_content_extracted"}` per CONTEXT.md decision.

**`trafilatura` `with_metadata=True` changes return type** (STACK): When `with_metadata=True` is set, `extract()` returns a JSON envelope, not a markdown string. Use `trafilatura.extract_metadata()` separately for metadata fields.

**`trafilatura` `only_with_metadata=True` silently drops content** (PITFALLS): Suppresses output for any page missing a parseable date, title, or URL — even pages with substantial content. Never use `only_with_metadata=True`. Extract text and metadata separately.

**`include_links` and `include_images` are experimental in trafilatura** (STACK): Use BeautifulSoup4 on the raw page HTML for link and image array extraction instead. Run trafilatura only for main content + metadata.

**5MB cap by character count instead of bytes** (PITFALLS): `len(markdown)` returns character count. Multi-byte Unicode (CJK, emoji) can double or triple the byte size. Always check `len(markdown.encode("utf-8"))` and truncate bytes, then decode with `errors="ignore"` to avoid splitting codepoints.

**Table extraction garbled on rowspan/colspan** (PITFALLS): Naive BS4 `<tr>`/`<td>` iteration produces misaligned rows for merged-cell tables. Use `pandas.read_html()` which handles span attributes correctly.

**SPA DOM may have no semantic structure** (PITFALLS): `page.content()` returns the post-JS DOM. For React/Vue SPAs, this is a `<div>` tree with no `<article>`, `<main>`, or `<p>` tags. Trafilatura may return `None`. Using `wait_for` to wait for a known content selector improves extraction quality. Document as a known limitation.

### Navigation

**`page.goto()` response is `None` on navigation failure** (PITFALLS): The return type is `Optional[Response]`. Always guard: `status_code = response.status if response else None`. Store `None` in metadata and add `"navigation_failed"` to warnings.

**Cloudflare challenge HTML looks like a successful page load** (PITFALLS): HTTP 403 or JS challenge pages are valid HTML. `page.goto()` succeeds (no exception). After navigation, check `response.status in (403, 429, 503)` AND check the first 2000 chars of HTML for `"Just a moment"` or `"cf-browser-verification"`. Return `{success: false, error: "blocked_by_protection"}`.

**`final_url` may be a `data:` or `blob:` URL** (PITFALLS): Some pages use JS navigation to `data:text/html,...` or `blob:` URLs. Sanitize `page.url` before returning: if it starts with `data:` or `blob:`, fall back to the original input URL and add `"navigation_to_non_http_url"` to warnings.

### SSRF

**`socket.gethostbyname()` is IPv4-only** (SECURITY): Returns one address. IPv6-only hosts bypass the SSRF check entirely. Always use `socket.getaddrinfo(hostname, None)` and check ALL returned addresses.

**IPv4-mapped IPv6 bypass** (SECURITY): `::ffff:192.168.1.1` may not be caught by `is_private` alone. Explicitly unwrap `ip.ipv4_mapped` and re-check before the standard `is_private` chain.

**Redirect-chain SSRF** (SECURITY, STACK): Pre-flight SSRF check validates the input URL only. Playwright follows redirects without re-checking. Implement a `page.route("**/*", ...)` handler that aborts `document` resource type navigations to private IPs.

**SSRF validation runs after payment if placed in handler body** (INTEGRATION, SECURITY): `fastapi-x402` operates at the ASGI middleware layer, above FastAPI's dependency injection. SSRF validation must run in a Starlette `BaseHTTPMiddleware` added AFTER `init_x402()` (LIFO ordering ensures it executes first).

### Railway / Docker

**`$PORT` not expanding in exec-form CMD** (INTEGRATION): `CMD ["uvicorn", ..., "$PORT"]` treats `$PORT` as a literal string. Use shell form: `CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`.

**Railway health check fails during Playwright startup** (INTEGRATION): Playwright browser takes ~10-15 seconds to launch. Set `healthcheckTimeout = 120` in `railway.toml`. Health endpoint must always return HTTP 200 (Railway checks status code only, not body fields).

**Railway OOM kill logged as exit code 137 only** (PITFALLS): No explicit OOM message in logs. Chromium headless uses 300-400MB; plus trafilatura/BS4 buffers; plus route-blocking race condition memory spikes. Minimum 1GB RAM required. Run `--workers 1` — multiple workers each launch a separate browser (300-400MB each), multiplying consumption.

**Route blocking must be active before `page.goto()`** (PITFALLS): Register `context.route()` before calling `page.goto()`. If route blocking is registered after navigation starts, resources are already loading.

**`page.route()` memory leak on long-running servers** (PITFALLS): Playwright accumulates `Request`/`Response` objects in `page`-level route handlers. Use `context.route()` instead — objects are cleared when `context.close()` is called (already in the `finally` block).

**`fixture.json` not found at runtime** (INTEGRATION): Requires an explicit `COPY fixture.json .` line in the Dockerfile (or `COPY . .`). The `COPY main.py .` pattern misses it.

**MCP tool uses GET for paid endpoint** (INTEGRATION): The paid endpoint is `POST /scrape` (JSON body). Use `apiPost` in the MCP tool handler for paid mode. Use `apiGet` only for the free `GET /scrape/test` endpoint.

### Rate Limiting

**Per-wallet rate limit attribute name unverified** (SECURITY): `request.state.x402_payer` is the expected attribute set by `fastapi-x402` after payment verification, but this is not documented in the library README. Inspect the library source before implementing. If unavailable, fall back to IP-based rate limiting.

**slowapi key reads proxy IP, not client IP** (SECURITY): Behind Railway's reverse proxy, `get_remote_address` reads `request.client.host` (the proxy IP). For the test endpoint at 100 req/hr, this is acceptable (conservative — rate-limits a whole data center).

---

## Code Examples

### Complete SSRF Validator

```python
import socket
import ipaddress
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

def validate_url_for_ssrf(url: str) -> None:
    """Raises ValueError if the URL targets a private/internal resource.
    Uses getaddrinfo (not gethostbyname) to catch both IPv4 and IPv6 records.
    Checks ALL resolved addresses."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed; only http/https accepted")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("No hostname in URL")

    # Reject bare IP literals that are already private
    try:
        direct_ip = ipaddress.ip_address(hostname)
        _assert_ip_public(direct_ip)
        return
    except ValueError:
        pass  # Not an IP literal

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

def _assert_ip_public(ip) -> None:
    # For IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.1), check the underlying IPv4
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        _assert_ip_public(ip.ipv4_mapped)
        return
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
        raise ValueError(f"URL resolves to blocked IP range: {ip}")
```

### Redirect-Chain SSRF Route Intercept

```python
async def abort_private_navigation(route):
    """Abort document-level navigations to private IPs (redirect-chain SSRF protection)."""
    if route.request.resource_type == "document":
        try:
            validate_url_for_ssrf(route.request.url)
        except ValueError:
            await route.abort("blockedbyclient")
            return
    await route.continue_()
```

Register on context (not page) to avoid memory leaks:
```python
await context.route("**/*", abort_private_navigation)
```

### Resource Blocking (Security + Memory)

```python
BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "websocket"}

async def handle_route(route):
    """Block non-content resource types before page.goto()."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()
```

Do NOT block `script` — required for SPA JS rendering (SCRAPE-02, SCRAPE-03).

### Cloudflare Detection

```python
def detect_block(response, html: str) -> Optional[str]:
    """Returns error code if page appears blocked, None otherwise."""
    status = response.status if response else None
    if status in (403, 429, 503):
        return "blocked_by_protection"
    # Check Cloudflare challenge markers in first 2000 chars
    if ("Just a moment" in html[:2000]
            or "cf-browser-verification" in html[:2000]
            or "Access denied" in html[:500]):
        return "blocked_by_protection"
    return None
```

### Fixture Structure (`fixture.json`)

```json
{
  "success": true,
  "url": "https://x402.org",
  "final_url": "https://x402.org/",
  "markdown": "# x402 Protocol\n\nThe x402 protocol enables pay-per-request APIs...",
  "links": [
    {"url": "https://x402.org/docs", "text": "Documentation"},
    {"url": "https://github.com/coinbase/x402", "text": "GitHub"}
  ],
  "tables": [
    {
      "headers": ["Network", "Token", "Status"],
      "rows": [["Base", "USDC", "Mainnet"], ["Base Sepolia", "USDC", "Testnet"]]
    }
  ],
  "images": [
    {"src": "https://x402.org/logo.png", "alt": "x402 logo"}
  ],
  "metadata": {
    "title": "x402 — Pay-Per-Request API Protocol",
    "description": "The open standard for machine-to-machine micropayments",
    "og_title": "x402 Protocol",
    "og_image": "https://x402.org/og-image.png",
    "canonical_url": "https://x402.org/",
    "language": "en",
    "status_code": 200,
    "content_type": "text/html; charset=utf-8",
    "content_language": null,
    "x_robots_tag": null
  },
  "warnings": []
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `python:3.11-slim` + 30+ `apt-get` packages + `playwright install chromium` | `FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy` | Eliminates apt layer, pre-bundled browsers, simpler Dockerfile |
| `wait_until="networkidle"` for SPA page load | `wait_until="domcontentloaded"` + explicit `wait_for_selector()` | Playwright officially discouraged `networkidle` ~2023; analytics-heavy pages no longer time out |
| `readability-lxml` (Mozilla) or `newspaper3k` | `trafilatura` 2.0 | Better boilerplate removal, native markdown output, metadata extraction in one library; `newspaper3k` unmaintained |
| `html2text` for markdown conversion | `trafilatura` with `output_format="markdown"` | Integrated pipeline: content extraction + markdown in one call |
| `page.wait_for_selector()` | `page.locator(sel).wait_for()` | `wait_for_selector` still functional; locator API preferred for tests; `wait_for_selector` remains practical for CSS-string API contract |
| Manual redirect-following IP check (TOCTOU-unsafe) | stdlib `socket.getaddrinfo()` pre-flight + Playwright `page.route()` abort | Pre-flight catches direct IPs and DNS names; route intercept catches redirect-chain SSRF |

**Deprecated / do not use:**
- `newspaper3k`: unmaintained since 2022
- `wait_until="networkidle"`: officially discouraged by Playwright team
- `socket.gethostbyname()`: IPv4-only; use `socket.getaddrinfo()` instead
- `page.route()` for resource blocking: use `context.route()` to avoid memory leaks
- `trafilatura.extract(..., only_with_metadata=True)`: silently drops content on metadata-sparse pages

---

## Open Questions

1. **Docker build validation (HIGH PRIORITY):** The switch from `python:3.11-slim` to `mcr.microsoft.com/playwright/python:v1.44.0-jammy` has not been validated locally for this project. Run `docker build` before Railway deploy. If the base image causes issues, the fallback is `python:3.10-slim` + `RUN apt-get install ...` + `playwright install chromium` (existing screenshot-api pattern).

2. **`request.state.x402_payer` attribute name:** The exact attribute set by `fastapi-x402` 0.1.8 after payment verification needs empirical validation. Inspect library source before implementing per-wallet rate limiting. Fallback: IP-based rate limiting on paid endpoint.

3. **SSRF middleware + fastapi-x402 middleware interaction:** The `SSRFMiddleware` + `init_x402()` LIFO ordering analysis is based on Starlette middleware documentation, not an empirical test with `fastapi-x402` 0.1.8. Validate during integration testing that SSRF 400 responses fire before payment is accepted.

4. **trafilatura metadata field names:** `trafilatura.extract_metadata()` returns a `Document` object. The exact field names for `og_title` need verification — `meta.image` maps to og:image, but `og_title` may be `meta.title` (the og:title may override the `<title>` tag). Check the `trafilatura.core.Document` class attribute list.

5. **Per-wallet rate limit for paid endpoint:** User constraint says "pick a reasonable number." Research recommendation is 200/hour per wallet ($4/hr ceiling). Confirm this is acceptable.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | No contradictions found. DIM-STACK and DIM-INTEGRATION both note the `@pay`/`@app.post` decorator order — they agree. DIM-STACK uses `socket.gethostbyname()`; DIM-SECURITY upgrades this to `socket.getaddrinfo()` — SECURITY supersedes STACK, no conflict. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples, State of the Art, Open Questions. User Constraints and Phase Requirements included. |
| Dimension Coverage | PASS | STACK: persistent browser, trafilatura, Docker image, rate limiting integrated. INTEGRATION: API contract schema, Railway config, MCP tool, SSRF pre-payment ordering integrated. SECURITY: `getaddrinfo`, IPv4-mapped IPv6, redirect-chain Playwright intercept, SSRFMiddleware, context hardening integrated. PITFALLS: all 13 pitfalls integrated into Common Pitfalls section. |
| Requirement Coverage | PASS | SCRAPE-01 through SCRAPE-05 all mapped in Phase Requirements table with explicit research support. |

---

## Sources

### Primary (HIGH confidence)

- PyPI `fastapi-x402` — version 0.1.8, dependencies, decorator order
- GitHub `jordo1138/fastapi-x402` README — `init_x402`, `@pay`, middleware execution order
- PyPI `trafilatura` — version 2.0.0, `extract()` parameters, `extract_metadata()` API
- trafilatura official docs (readthedocs.io) — `output_format`, `with_metadata`, `only_with_metadata`, `include_links`/`include_images` experimental status
- playwright.dev/python/docs/docker — base image naming, `--no-sandbox` for root user
- playwright.dev/python/docs/release-notes — v1.44.0 Chromium 125
- playwright.dev/python/docs/api/class-browser — `browser.is_connected()`, `on("disconnected")`, disposal semantics
- Playwright Python docs — `page.goto()` return type `Optional[Response]`, per-action timeout semantics
- `/Users/jameswisdom/projects/usdc-screenshot-api/screenshot-api/main.py` — existing lifespan pattern
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — APIS dict, tool registration, `apiGet`/`apiPost`/`textResult`/`errorResult` helpers
- Python stdlib docs — `ipaddress` module properties; `socket.getaddrinfo()` vs `gethostbyname()`
- Python docs — `str.encode("utf-8")`, `len()` on str vs bytes
- CPython issue #77614 — `is_private` bug for IPv4-mapped IPv6, fixed Python 3.10
- Pydantic docs — `HttpUrl`, `UrlConstraints`, `Annotated` pattern
- slowapi docs — `key_func`, `@limiter.limit()`, `get_remote_address`
- Railway config-as-code docs — `healthcheckPath`, `healthcheckTimeout`, `restartPolicyType`
- Playwright Python GitHub issues #462, #723 — `sync_playwright` in asyncio context
- Playwright GitHub issues #1754, #4511, #6319 — `page.route()` memory leak; `context.route()` mitigation
- trafilatura readthedocs — `only_with_metadata` behavior confirmed

### Secondary (MEDIUM confidence)

- OWASP SSRF Prevention Cheat Sheet — resolve all A+AAAA records; `ipaddress` for validation
- Drawbridge library README — redirect-chain SSRF protection via transport-layer pinning
- OpenClaw GHSA-jrvc-8ff5-2f9f — IPv4-mapped IPv6 SSRF bypass via `0:0:0:0:0:ffff:7f00:1`
- WebSearch confirming Cloudflare 403/JS challenge is valid HTML; "Just a moment" detection pattern
- pandas docs — `read_html()` rowspan/colspan handling, `lxml` backend
- Railway Help Station — exit code 137 = OOM kill; headless Chrome memory requirements
- Railway community — PORT shell expansion, `--host 0.0.0.0` required for IPv4 proxy

### Tertiary (LOW confidence)

- `request.state.x402_payer` attribute name in `fastapi-x402` 0.1.8 — not verified against source
- SSRFMiddleware + `init_x402()` LIFO ordering — derived from Starlette middleware docs, not empirically tested
- `data:`/`blob:` final_url from JS navigation — reported in community; frequency in production unknown
- Memory spike estimates (200MB unblocked images, 100MB large HTML in trafilatura) — community profiling reports, not measured for this configuration
- `service_workers="block"` preventing cross-context persistence — theoretically correct, not verified against a test case

---

## Metadata

**Confidence breakdown:**
- STACK: HIGH — primary sources from official PyPI APIs, docs, existing project code
- INTEGRATION: HIGH — primary sources from existing `src/index.ts`, screenshot-api code, Railway docs
- SECURITY: HIGH — primary sources from official Python stdlib docs, Playwright Docker docs, CPython issues
- PITFALLS: HIGH — 10 of 13 pitfalls from official docs/GitHub issues; 3 from community-verified patterns

**Overall confidence:** HIGH (all four dimensions HIGH)

**Research date:** 2026-03-12
**Valid until:** 2026-09-12 — Playwright, trafilatura, Railway stable; check if Playwright adds browser reconnect support

**Dimensions researched:** STACK, INTEGRATION, SECURITY, PITFALLS (4 of 4)
