# Phase 15: Shallow Site Crawl - Research

**Researched:** 2026-03-18
**Domain:** Python BFS crawler on FastAPI/Playwright scraping API
**Confidence:** HIGH
**Method:** MECE decomposition (3 dimensions: INTEGRATION, SECURITY, PITFALLS)

---

## Summary

Phase 15 adds a `POST /crawl` endpoint to the existing `x402-scraping-api/main.py`. The endpoint accepts a seed URL, crawls up to 15 pages via breadth-first search, and returns per-page extraction results in the same schema as the existing `/scrape` endpoint. No new runtime dependencies are needed: all required tools (`collections.deque`, `fnmatch`, `urllib.parse`) are Python stdlib, and the BFS loop reuses the existing `scrape_page()` + `extract_content()` pipeline that is already battle-tested in production.

Security is the primary design constraint. The crawl endpoint introduces a new attack surface: discovered URLs from page content are attacker-controlled inputs that are invisible to the existing `SSRFMiddleware`. The three-layer SSRF defense must be preserved: (1) SSRFMiddleware validates the seed URL before payment, (2) `validate_url_for_ssrf()` is called inside the BFS loop before every discovered URL is enqueued, and (3) the existing `abort_private_navigation` Playwright route handler catches redirect chains at navigation time. All three layers are pre-existing in the codebase; they require extension, not new implementation.

The key implementation pitfalls are URL normalization (trailing slashes and fragments cause duplicate crawls), seed netloc drift (seed URL may redirect to a different hostname, breaking same-origin checks), and per-page timeout stacking (15 pages at 8s each = 120s max; Railway's HTTP timeout is 15 minutes so this is safe). A companion `GET /crawl/test` endpoint serves fixture data for the free test path. Phase 15 is backend-only; the MCP tool registration (`x402_crawl_site` in `src/index.ts`) belongs to Phase 16.

**Primary recommendation:** Implement the BFS crawl as ~80 lines of Python in `main.py`, extending the existing SSRF and scraping infrastructure — no new libraries.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CRAWL-01 | User can crawl a site via new x402_crawl_site MCP tool (POST /crawl endpoint) | Backend `POST /crawl` route registered in `main.py` with `CrawlRequest` schema; MCP registration is Phase 16 (INTEGRATION) |
| CRAWL-02 | Crawl respects max_pages (default 10, max 15) and max_depth (default 2, max 5) | `CrawlRequest` Pydantic fields with `ge`/`le` validators; BFS loop has `while queue and len(results) < max_pages` + `if depth < max_depth` guards (INTEGRATION, SECURITY) |
| CRAWL-03 | Crawl returns per-page results in same schema as /scrape | `PageResult` schema mirrors `/scrape` response exactly, plus `"depth": int` field (INTEGRATION) |
| CRAWL-04 | All discovered URLs pass SSRF validation before being fetched | `validate_url_for_ssrf()` called in BFS loop before enqueue; SSRFMiddleware covers seed URL; `abort_private_navigation` covers redirect chains (SECURITY, PITFALLS) |
| CRAWL-05 | Crawl supports include/exclude path filters (e.g., `/blog/*`) | `_passes_path_filter()` with `fnmatch.fnmatch()` on URL path component; path normalized with `posixpath.normpath()` before matching (INTEGRATION, SECURITY) |
| CRAWL-06 | Response includes metadata: pages_requested, pages_crawled, pages_skipped, reasons_skipped | Top-level crawl response schema includes all four fields; updated correctly on per-page failure (INTEGRATION, PITFALLS) |
| CRAWL-07 | Partial success — returns results for pages crawled even if some fail | Per-page `try/except` in BFS loop; only `HTTPException(503)` aborts crawl; all other errors recorded as failed `PageResult` entries (PITFALLS) |
| CRAWL-08 | Free test endpoint at GET /crawl/test returns fixture data | `@app.get("/crawl/test")` with `crawl_fixture.json`; pattern matches existing `/scrape/test`; fixture must be copied in Dockerfile (INTEGRATION) |

---

## Standard Stack

No new runtime dependencies are required for Phase 15. The complete stack is:

**Existing `requirements.txt` (unchanged):**
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
playwright==1.44.0
fastapi-x402>=0.1.8
trafilatura>=2.0.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
slowapi>=0.1.9
pandas>=2.0.0
```

**Stdlib modules used by the crawl layer (all already importable):**
```python
from urllib.parse import urljoin, urlparse  # already imported in main.py line 17
from collections import deque               # stdlib
import fnmatch                              # stdlib
import posixpath                            # stdlib (path normalization)
```

**Do not add `crawlee[playwright]`.** crawlee 1.5.0 requires `playwright>=1.27.0`, which is technically compatible with the pinned `playwright==1.44.0`, but crawlee spawns its own `BrowserPool` (conflicts with existing `browser` global), writes to disk by default (not suitable for sync in-memory collection), and adds ~15MB install overhead. The 15-page sync crawl does not need a crawl framework.

**Dockerfile additions required:**
```dockerfile
COPY crawl_fixture.json .   # add alongside existing COPY fixture.json .
```

---

## Architecture Patterns

### BFS Crawl Flow

```
POST /crawl (seed_url, max_pages=10, max_depth=2, include_paths, exclude_paths)
    │
    ├─ SSRFMiddleware validates seed_url BEFORE payment (pre-payment SSRF gate)
    ├─ @pay("$0.10") — x402 payment accepted
    ├─ browser health check (503 if browser is None or disconnected)
    │
    └─ run_bfs_crawl(seed_url, ...)
           │
           ├─ queue: deque [(seed_url, depth=0)]
           ├─ visited: set {normalize_url(seed_url)}
           │
           └─ LOOP while queue and len(results) < max_pages:
                  │
                  ├─ (url, depth) = queue.popleft()   ← FIFO = true BFS
                  │
                  ├─ scrape_page(url, wait_for=None)  ← reuses existing function
                  ├─ extract_content(html, final_url) ← reuses existing function
                  │
                  ├─ add final_url to visited (redirect loop protection)
                  ├─ append PageResult to results[]
                  │
                  └─ IF depth < max_depth:
                         └─ FOR each link in extracted["links"]:
                                ├─ resolve: urljoin(final_url, href)
                                ├─ normalize_url()
                                ├─ skip if scheme not http/https
                                ├─ skip if in visited
                                ├─ validate_url_for_ssrf()   ← SSRF on every URL
                                ├─ is_same_domain() check    ← same netloc as seed
                                ├─ _passes_path_filter()     ← include/exclude
                                └─ enqueue (normalized_url, depth + 1)
```

### Key Architectural Decisions

**1. `collections.deque` as FIFO = true BFS.**
`popleft()` on a deque is O(1). Using `list.pop(0)` would be O(n) per dequeue and would produce the wrong traversal order. All depth-1 pages must be visited before any depth-2 pages.

**2. Reuse `scrape_page()` and `extract_content()` without modification.**
These functions encapsulate the entire Playwright context lifecycle (create, route handlers, navigate, extract, close). The crawl layer only drives the queue; it does not manage browser contexts directly.

**3. `wait_for=None` for all crawl pages.**
The `wait_for` CSS selector (SPA support) is not exposed on the crawl endpoint. Callers cannot specify per-page selectors in a batch crawl request.

**4. Per-page timeout is independent, not shared.**
Each call to `scrape_page()` has its own 8-second (or shorter; see Pitfalls) budget. A 15-page crawl can legitimately take up to 120 seconds. Railway's HTTP timeout is 15 minutes — this is safe.

**5. `seed_netloc` derived from first page's `final_url`, not input URL.**
If `https://example.com` redirects to `https://www.example.com/`, the input netloc (`example.com`) will cause all internal links to fail the same-origin check. After fetching the seed page, re-derive `seed_netloc` from `final_url`.

**6. Same-origin enforcement is implicit, not a user parameter.**
Only links matching `urlparse(candidate_url).netloc == seed_netloc` are enqueued. Off-domain links are silently counted as `pages_skipped` with reason `"off_domain"`. Subdomain following is out of scope.

**7. Sequential execution, not concurrent.**
No `asyncio.gather()` over the BFS queue. Concurrent browser contexts on Railway's 512MB container risk OOM. Sequential execution at 6-8s/page is within the timeout budget.

**8. Partial success model matches `/scrape`.**
The top-level `success` field is `True` if at least one page succeeded. Failed pages appear in `results[]` with `success: False`. Only `HTTPException(503)` (browser unavailable) aborts the crawl entirely.

### Request/Response Schemas

**`CrawlRequest`:**
```python
class CrawlRequest(BaseModel):
    url: BoundedHttpUrl = Field(
        ..., description="Seed URL (http/https, max 2048 chars)"
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
```

**Top-level crawl response:**
```python
{
    "success": bool,            # True if >= 1 page succeeded
    "seed_url": str,
    "pages_requested": int,     # URLs attempted (success + failed)
    "pages_crawled": int,       # Pages returning content (success=True)
    "pages_skipped": int,       # Filtered, SSRF-blocked, off-domain, error
    "reasons_skipped": list[str],  # deduplicated reason codes
    "results": list[PageResult],
}
```

**`PageResult`** (identical to `/scrape` response + `"depth"` field):
```python
{
    "success": bool,
    "url": str,
    "final_url": str,
    "depth": int,               # BFS depth: 0 = seed
    "markdown": str | None,
    "links": list[{"url": str, "text": str}],
    "tables": list[{"headers": list, "rows": list}],
    "images": list[{"src": str, "alt": str}],
    "metadata": {
        "title": str | None,
        "description": str | None,
        "og_title": str | None,
        "og_image": str | None,
        "canonical_url": str | None,
        "language": str | None,
        "status_code": int | None,
        "content_type": str | None,
        "content_language": str | None,
        "x_robots_tag": str | None,
    },
    "warnings": list[str],
    # error fields present only when success=False:
    "error": str | None,
    "detail": str | None,
}
```

### Fixture Structure (`crawl_fixture.json`)

The fixture must include at least one success and one failure entry to demonstrate CRAWL-07 partial success behavior. Seed site: `https://usebismuth.com` (owned by the project).

```json
{
  "success": true,
  "seed_url": "https://usebismuth.com",
  "pages_requested": 3,
  "pages_crawled": 2,
  "pages_skipped": 1,
  "reasons_skipped": ["timeout"],
  "results": [
    {
      "success": true,
      "url": "https://usebismuth.com",
      "final_url": "https://usebismuth.com/",
      "depth": 0,
      "markdown": "# Bismuth\n\nPay-per-use APIs for AI agents...",
      "links": [{"url": "https://usebismuth.com/apis/scraping", "text": "Web Scraping API"}],
      "tables": [], "images": [],
      "metadata": {"title": "Bismuth — Pay-Per-Use APIs for AI Agents", "status_code": 200, ...},
      "warnings": []
    },
    {
      "success": true,
      "url": "https://usebismuth.com/apis/scraping",
      "final_url": "https://usebismuth.com/apis/scraping/",
      "depth": 1,
      "markdown": "# Web Scraping API\n\nScrape any URL...",
      "links": [], "tables": [], "images": [],
      "metadata": {"title": "Web Scraping API — Bismuth", "status_code": 200, ...},
      "warnings": []
    },
    {
      "success": false,
      "url": "https://usebismuth.com/apis/file-conversion",
      "depth": 1,
      "error": "timeout",
      "detail": "Page load timed out after 8.0s.",
      "warnings": ["timeout"]
    }
  ]
}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSRF IP validation | Custom regex or string matching for private ranges | `ipaddress` stdlib — `ip.is_private`, `ip.is_loopback`, `ip.is_link_local`, `ip.is_multicast`, `ip.is_reserved`, `ip.is_unspecified` | RFC1918, loopback, link-local, reserved, and unspecified ranges are already enumerated. Regex misses subnets and IPv6 variants. (SECURITY) |
| DNS all-records lookup | `socket.gethostbyname()` single-record lookup | `socket.getaddrinfo()` | `gethostbyname` returns one record; a hostname can resolve to both public IPv4 and private IPv6. `getaddrinfo` surfaces all A + AAAA records. Already in the project — copy it. (SECURITY) |
| IPv4-mapped IPv6 unwrapping | Manual string slicing on `::ffff:x.x.x.x` | `ipaddress.IPv6Address.ipv4_mapped` attribute | Already handled in `_assert_ip_public()` in `main.py`. Do not diverge. (SECURITY) |
| BFS queue | Custom class or `list` | `collections.deque` of `(url, depth)` tuples | O(1) `popleft()`; deque as FIFO is true BFS. Already stdlib. (PITFALLS) |
| URL deduplication | Custom hash/cache class | Python `set` of normalized URL strings | O(1) lookup; normalization is 5 lines. (PITFALLS) |
| Per-page timeout | Custom threading timer | Playwright's own `timeout` parameter in `page.goto()` | Keeps cleanup inside `scrape_page()`'s `finally` block; avoids asyncio cancellation leaks. (PITFALLS) |
| Overall crawl budget | Polling loop with `time.sleep` | `time.monotonic()` check before each BFS iteration | Already the pattern in `scrape_page()`; zero deps. (PITFALLS) |
| Path filter matching | Regex engine or custom glob | `path.startswith(prefix)` after stripping `/*` suffix (or `fnmatch.fnmatch()`) | Regex for `/blog/*` is over-engineered. `startswith` is unambiguous for prefix patterns. (PITFALLS) |
| HTML link extraction | Custom link parser | Existing `BeautifulSoup` pipeline in `extract_content()` | Already in requirements.txt and production-tested. (PITFALLS) |
| Redirect loop detection | Graph cycle algorithm | Add `final_url` to visited set after each fetch | The visited set already tracks this; no separate structure needed. (PITFALLS) |
| Crawl framework | `crawlee[playwright]` | Manual BFS loop (~80 lines) | crawlee conflicts with existing `browser` global, writes to disk by default, adds 15MB overhead. Incompatible with sync in-memory collection pattern. (INTEGRATION) |

---

## Common Pitfalls

### 1. SSRF Only on Seed URL — BFS Discovered URLs Bypass Validation (CRITICAL)

**What goes wrong:** `SSRFMiddleware` validates the `seed_url` before payment. Links discovered during BFS (from attacker-controlled page content) are never seen by the middleware. A crawl of `http://trusted.example.com` could fetch `http://169.254.169.254/latest/meta-data/` if an internal link points there.

**How to avoid:** Call `validate_url_for_ssrf(candidate_url)` inside the BFS link-discovery loop before enqueueing any URL. On `ValueError`: skip with reason `"ssrf_blocked"`, do NOT raise HTTP 400 (it would abort the entire crawl). This is the STATE.md pre-merge security gate.

**Three-layer defense required:**
1. `SSRFMiddleware` — seed URL before payment
2. `validate_url_for_ssrf()` in BFS loop — every discovered URL before enqueue
3. `abort_private_navigation` Playwright route handler — every actual navigation (catches redirect chains)

All three layers are already in `main.py`; they require extension to cover `/crawl`, not reimplementation. [SECURITY + PITFALLS]

---

### 2. SSRFMiddleware Path Check Not Extended to `/crawl`

**What goes wrong:** Existing `SSRFMiddleware` checks `request.url.path == "/scrape"`. A POST to `/crawl` bypasses pre-payment SSRF validation on the seed URL.

**How to avoid:** Change the condition to:
```python
if request.method == "POST" and request.url.path in ("/scrape", "/crawl"):
```
[INTEGRATION + SECURITY]

---

### 3. URL Normalization — Trailing Slash and Fragment Duplicates

**What goes wrong:** `https://example.com/about` and `https://example.com/about/` are treated as different URLs. `https://example.com/page#section` and `https://example.com/page#other` are the same HTTP resource but different strings.

**How to avoid:** Normalize URLs before adding to the visited set:
```python
import posixpath
from urllib.parse import urlparse, urlunsplit

def normalize_url(url: str) -> str:
    p = urlparse(url)
    path = posixpath.normpath(p.path)
    if p.path.endswith("/") and not path.endswith("/"):
        path += "/"
    # Strip fragment; preserve query string
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))
```
Do NOT strip query strings (they are server-side resource identifiers). stripping `utm_*` params is a future requirement (CRAWL-F03). [PITFALLS]

---

### 4. Seed Netloc Drift After Redirect

**What goes wrong:** Seed URL `https://example.com` redirects to `https://www.example.com/`. All discovered links have netloc `www.example.com`, which fails the same-origin check, so nothing beyond the seed gets crawled.

**How to avoid:** After fetching the seed page, re-derive `seed_netloc` from `final_url`, not the input URL:
```python
seed_result = await scrape_page(seed_url, wait_for=None)
seed_netloc = urlparse(seed_result["final_url"]).netloc.lower()
```
[PITFALLS]

---

### 5. Cross-Domain Link Leak — Protocol-Relative URLs

**What goes wrong:** `<a href="//evil.com/payload">` at `http://example.com/page`. `urljoin("http://example.com/page", "//evil.com/payload")` returns `"http://evil.com/payload"`. A naive netloc check on the raw href text fails.

**How to avoid:** Always resolve hrefs with `urljoin(final_url, href)` first, then pass the fully-resolved absolute URL to `is_same_domain()` and `validate_url_for_ssrf()`. Never filter raw href strings. [SECURITY]

---

### 6. Path Filter Bypass via Relative Path Traversal

**What goes wrong:** `fnmatch.fnmatch("/blog/../admin/config", "/blog/*")` returns `True` because `*` matches `../admin/config`. An include filter intended to allow only `/blog/*` inadvertently allows `/blog/../admin/config`.

**How to avoid:** Apply `posixpath.normpath()` to the URL path before fnmatch matching:
```python
import posixpath

def _passes_path_filter(path: str, include_paths: list[str], exclude_paths: list[str]) -> bool:
    normalized = posixpath.normpath(path)
    if include_paths:
        if not any(fnmatch.fnmatch(normalized, pat) for pat in include_paths):
            return False
    if exclude_paths:
        if any(fnmatch.fnmatch(normalized, pat) for pat in exclude_paths):
            return False
    return True
```
Note: `urljoin()` + `urlparse()` normalize relative paths before the path is extracted, so this is a defense-in-depth measure, but `posixpath.normpath()` is cheap and explicit. [SECURITY]

---

### 7. fnmatch `*` Crosses `/` — `/blog/*` Does Not Match `/blog` (No Trailing Slash)

**What goes wrong:** `fnmatch.fnmatch("/blog", "/blog/*")` returns `False` — the trailing `/*` requires at least one character after the slash. A user providing `include=["/docs/*"]` gets zero results because the root `/docs` page is filtered out before its links are discovered.

**How to avoid:** For prefix-style patterns (ending in `/*`), also match the bare path without the trailing `/*`:
```python
# Normalize filter: "/blog/*" also matches "/blog"
def _expand_pattern(pat: str) -> list[str]:
    if pat.endswith("/*"):
        return [pat, pat[:-2]]  # e.g. ["/blog/*", "/blog"]
    return [pat]
```
Or document clearly that `/blog/*` matches `/blog/anything` but not `/blog` itself, and callers must add `/blog` explicitly. [PITFALLS]

---

### 8. Per-Page Timeout Stacking — Use Shorter Per-Page Budget for Crawl

**What goes wrong:** The existing `TOTAL_BUDGET_S = 8.0` is appropriate for a single-page scrape. At 15 pages × 8s = 120s max, the crawl stays within Railway's 15-minute HTTP timeout. However, on slow sites, pages 1-5 each taking 7-8s leaves only 60-80 seconds for pages 6-15. The crawler may exhaust its real-world patience budget even if it's technically within limits.

**How to avoid:** Use a shorter per-page timeout for crawl pages (e.g., 6 seconds) via a `crawl_page_timeout` constant. Set an overall crawl wall-clock budget (e.g., 90 seconds) checked at the top of each BFS iteration:
```python
CRAWL_PAGE_BUDGET_S = 6.0
CRAWL_TOTAL_BUDGET_S = 90.0

crawl_start = time.monotonic()
while queue and len(results) < max_pages:
    if time.monotonic() - crawl_start > CRAWL_TOTAL_BUDGET_S:
        top_level_warnings.append("crawl_timeout")
        break
    url, depth = queue.popleft()
    # ...
```
On timeout: return partial results with `crawl_timeout` in `reasons_skipped`. Do not raise 504. [PITFALLS]

---

### 9. Per-Page Partial Failure — Don't Re-Raise, Accumulate

**What goes wrong:** `scrape_page()` raises `HTTPException(503)` for browser unavailable. A naive crawl loop that re-raises this at the loop level returns a 503 with no crawl results, violating CRAWL-07.

**How to avoid:** Wrap each `scrape_page()` call:
```python
try:
    page_data = await scrape_page(url, wait_for=None)
except HTTPException as e:
    if e.status_code == 503:
        # Hard failure — browser dead, abort crawl with partial results
        top_level_warnings.append("browser_unavailable")
        break
    # Other HTTPException: record as failed page, continue
    results.append({"success": False, "url": url, "depth": depth,
                    "error": "http_error", "detail": str(e.detail), "warnings": []})
    pages_skipped += 1
    reasons_skipped.append("http_error")
    continue
except Exception as e:
    results.append({"success": False, "url": url, "depth": depth,
                    "error": "scrape_error", "detail": str(e), "warnings": []})
    pages_skipped += 1
    reasons_skipped.append("scrape_error")
    continue
```
[PITFALLS]

---

### 10. `crawl_fixture.json` Not in Dockerfile

**What goes wrong:** `GET /crawl/test` returns 500 `FileNotFoundError` at runtime.

**How to avoid:** Add `COPY crawl_fixture.json .` to the Dockerfile alongside `COPY fixture.json .`. [INTEGRATION]

---

### 11. `asyncio.wait_for` Cancellation Can Leak Playwright Contexts

**What goes wrong:** If `asyncio.wait_for(scrape_page(...), timeout=X)` times out, the coroutine is cancelled. If `context.close()` in the `finally` block does not complete before cancellation propagates, the Playwright context leaks.

**How to avoid:** Set per-page timeouts within `scrape_page()` via Playwright's `page.goto(url, timeout=per_page_ms)`, not via external `asyncio.wait_for()`. Use `asyncio.wait_for()` only at the crawl loop level for the overall budget (where cancellation is clean). [PITFALLS]

---

### 12. include/exclude Filter Lists Allow CPU Exhaustion

**What goes wrong:** 1000 patterns × 500 links per page × 15 pages = 7,500,000 `fnmatch` calls per request.

**How to avoid:** Cap list length in Pydantic model: `max_length=20`. Cap individual pattern length: `len(pat) > 200` raises `ValueError`. Both caps already shown in `CrawlRequest` above. [SECURITY]

---

### 13. DNS Rebinding / TOCTOU — Residual Risk

**What goes wrong:** `validate_url_for_ssrf()` calls `socket.getaddrinfo()` to validate all resolved IPs. An attacker-controlled DNS server returns a public IP on validation, then flips to a private IP for Playwright's actual request (TTL=0).

**How to avoid:** `abort_private_navigation` (Playwright route handler) provides mitigation by re-validating at actual navigation time. This is not a full TOCTOU fix (DNS layer is still unsynchronized) but is the best available mitigation without a custom pinning DNS resolver. Accept as residual risk, document in STATE.md. [SECURITY]

---

## Code Examples

### Core BFS Implementation

```python
from collections import deque
from urllib.parse import urljoin, urlparse, urlunsplit
import fnmatch
import posixpath
import time

CRAWL_PAGE_BUDGET_S = 6.0
CRAWL_TOTAL_BUDGET_S = 90.0


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase scheme+host, strip fragment,
    normalize path (collapse ./..), preserve query string."""
    p = urlparse(url)
    path = posixpath.normpath(p.path) if p.path else "/"
    if p.path.endswith("/") and not path.endswith("/"):
        path += "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def _passes_path_filter(path: str, include_paths: list[str], exclude_paths: list[str]) -> bool:
    normalized = posixpath.normpath(path)
    if include_paths:
        if not any(fnmatch.fnmatch(normalized, pat) for pat in include_paths):
            return False
    if exclude_paths:
        if any(fnmatch.fnmatch(normalized, pat) for pat in exclude_paths):
            return False
    return True


async def run_bfs_crawl(
    seed_url: str,
    max_pages: int,
    max_depth: int,
    include_paths: list[str],
    exclude_paths: list[str],
) -> dict:
    results = []
    reasons_skipped: list[str] = []
    pages_skipped = 0
    top_level_warnings: list[str] = []

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    norm_seed = normalize_url(seed_url)
    queue.append((seed_url, 0))
    visited.add(norm_seed)

    seed_netloc: str | None = None  # derived from first page's final_url
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
                top_level_warnings.append("browser_unavailable")
                break
            results.append({"success": False, "url": url, "depth": depth,
                             "error": "http_error", "detail": str(e.detail), "warnings": []})
            pages_skipped += 1
            reasons_skipped.append("http_error")
            continue
        except Exception as e:
            results.append({"success": False, "url": url, "depth": depth,
                             "error": "scrape_error", "detail": str(e), "warnings": []})
            pages_skipped += 1
            reasons_skipped.append("scrape_error")
            continue

        html = page_data["html"]
        final_url = page_data["final_url"]
        status_code = page_data["status_code"]
        response = page_data["response"]
        extra_warnings = page_data["extra_warnings"]

        # Derive seed_netloc from first page's final_url (handles seed redirects)
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

                # SSRF gate — must be first
                try:
                    validate_url_for_ssrf(resolved)
                except ValueError:
                    pages_skipped += 1
                    reasons_skipped.append("ssrf_blocked")
                    visited.add(norm)
                    continue

                # Same-origin gate
                if parsed.netloc.lower() != seed_netloc:
                    pages_skipped += 1
                    reasons_skipped.append("off_domain")
                    visited.add(norm)
                    continue

                # Path filter gate
                if not _passes_path_filter(parsed.path, include_paths, exclude_paths):
                    pages_skipped += 1
                    reasons_skipped.append("path_filter")
                    visited.add(norm)
                    continue

                visited.add(norm)
                queue.append((resolved, depth + 1))

    succeeded = [r for r in results if r.get("success")]
    return {
        "success": len(succeeded) > 0,
        "seed_url": seed_url,
        "pages_requested": len(results) + pages_skipped,
        "pages_crawled": len(succeeded),
        "pages_skipped": pages_skipped,
        "reasons_skipped": list(set(reasons_skipped)),
        "results": results,
        "warnings": top_level_warnings if top_level_warnings else None,
    }
```

### SSRFMiddleware Extension

```python
class SSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path in ("/scrape", "/crawl"):
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                url = body.get("url", "")
                if url:
                    validate_url_for_ssrf(str(url))
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"SSRF validation failed: {e}"},
                )
            except (json.JSONDecodeError, Exception):
                pass
        return await call_next(request)
```

### POST /crawl Route

```python
@app.post("/crawl")
@pay("$0.10")   # price TBD during planning — placeholder
async def crawl(request: Request, body: CrawlRequest):
    """Shallow BFS crawl — up to 15 pages, returns per-page extraction results."""
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
```

### GET /crawl/test Route

```python
@app.get("/crawl/test")
@limiter.limit("100/hour")
async def crawl_test(request: Request):
    """Free test endpoint — returns fixture data (no live crawl, no payment required)."""
    return load_crawl_fixture()
```

`load_crawl_fixture()` follows the existing `load_fixture()` pattern in `main.py`.

---

## State of the Art

**crawlee-python v1.5.0** (released 2026-03-06): supports `max_requests_per_crawl`, `max_crawl_depth`, and `Glob`-based `include`/`exclude` path filtering via `EnqueueLinksFunction`. The crawlee `BrowserPool` architecture is designed for high-throughput multi-worker crawling. For a 15-page sync endpoint that reuses an existing browser global, crawlee is the wrong abstraction — the benefit of a framework (queue management, concurrency) is a liability at this scale.

**Firecrawl and Crawl4AI** are hosted crawl services. They are out of scope for this project. Their path filter documentation was cross-referenced to validate the `fnmatch` pattern semantics.

**Python `ipaddress` module** (stdlib since 3.3): the canonical way to check SSRF IP ranges. All private IPv4 ranges (RFC1918), loopback, link-local, multicast, reserved, and unspecified are enumerated. IPv4-mapped IPv6 (`::ffff:x.x.x.x`) must be unwrapped via `.ipv4_mapped` before checking — already handled in the project's `_assert_ip_public()`.

**DNS rebinding mitigations**: The architectural gap between `getaddrinfo()` validation and Playwright's actual DNS resolution is a known class of SSRF bypass (CVE-2026-27127 on Craft CMS demonstrates the attack in 2026). The `abort_private_navigation` Playwright route handler provides meaningful mitigation for redirect-chain attacks but not pure DNS rebinding. A caching DNS resolver that pins results (e.g., custom DNS middleware) would close the gap but is deferred.

---

## Open Questions

1. **Pricing for `POST /crawl`**: The `$0.10` placeholder in the code examples must be confirmed during planning. The rate should reflect compute cost for up to 15 pages (each page roughly comparable to one `/scrape` call at `$0.01`). Range: `$0.05–$0.20`.

2. **`warnings` field in top-level crawl response**: The `run_bfs_crawl` code example returns a `"warnings"` key for crawl-level signals (`"crawl_timeout"`, `"browser_unavailable"`). This is not in the CRAWL-06 schema. Include it or fold into `reasons_skipped`? Recommend: include as optional field (omit if empty) for clarity.

3. **`www.` vs bare domain on same-origin check**: If the caller provides `https://example.com` and the site canonically lives at `https://www.example.com`, the `seed_netloc` drift fix (Pitfall 4) handles the redirect case. But what if the seed URL itself does NOT redirect, and some links use `www.` while others don't? This is an edge case; for now, treat `example.com` and `www.example.com` as different netlocs (strict matching, no www-stripping). Document this.

4. **Railway request timeout for long crawls**: Railway's default HTTP timeout is reported as 60 seconds in docs/community, but the Railway Help Station confirmed 15 minutes. The 90-second overall crawl budget (CRAWL_TOTAL_BUDGET_S) stays within the safer 60-second assumption and provides consistent behavior regardless of plan tier. Confirm actual timeout in Railway dashboard before launch.

5. **`include`/`exclude` naming in `CrawlRequest`**: DIM-INTEGRATION uses `include_paths`/`exclude_paths` as field names. DIM-SECURITY uses `include`/`exclude`. Standardize to `include_paths`/`exclude_paths` for clarity (matches REQUIREMENTS.md description "path filters").

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on core decisions: no crawlee, manual BFS, `validate_url_for_ssrf()` in BFS loop, sequential execution. DIM-INTEGRATION uses field names `include_paths`/`exclude_paths`; DIM-SECURITY uses `include`/`exclude` — resolved in favor of `include_paths`/`exclude_paths` (Open Question 5). |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples, State of the Art. Phase Requirements and Open Questions sections also present. |
| Dimension Coverage | PASS | INTEGRATION findings: endpoint schema, BFS implementation, fixture, SSRFMiddleware extension, Railway timeout, MCP awareness. SECURITY findings: `validate_url_for_ssrf()` implementation, `is_same_domain()`, `abort_private_navigation`, `posixpath.normpath()` for path bypass, resource exhaustion guards. PITFALLS findings: per-page timeout stacking, crawlee version risk, URL normalization, netloc drift, redirect loops, memory pressure, fnmatch semantics, partial failure handling. All integrated. |
| Requirement Coverage | PASS | CRAWL-01 through CRAWL-08 all mapped in Phase Requirements table above. |

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — `scrape_page()`, `extract_content()`, `SSRFMiddleware`, `validate_url_for_ssrf()`, `_assert_ip_public()`, `abort_private_navigation`, `ScrapeRequest`, browser lifespan, endpoint patterns, `TOTAL_BUDGET_S`
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/requirements.txt` — `playwright==1.44.0` pin confirmed
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/Dockerfile` — `FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy`, COPY file pattern
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/fixture.json` — `/scrape` response schema (canonical reference for CRAWL-03)
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — APIS dict, tool registration, `apiPost`/`apiGet`/`textResult`/`errorResult` patterns
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/STATE.md` — SSRF pre-merge security gate; crawlee[playwright] concern; Railway timeout
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/REQUIREMENTS.md` — CRAWL-01 through CRAWL-08
- Python stdlib docs — `collections.deque`, `fnmatch.fnmatch()`, `urllib.parse`, `posixpath.normpath`, `ipaddress`, `socket.getaddrinfo`
- Railway Help Station — HTTP timeout confirmed 15 minutes

### Secondary (MEDIUM confidence — official documentation)

- crawlee-python v1.5.0 pyproject.toml — `playwright>=1.27.0` requirement confirmed
- crawlee.dev/python/api — BrowserPool architecture, `EnqueueLinksFunction` Glob patterns
- GitHub apify/crawlee-python issue #1621 — `push_data`/`get_data()` may lose items (confirms crawlee storage is unsuitable for sync in-memory collection)
- OWASP SSRF Prevention Cheat Sheet — "Retrieve all A + AAAA records"; redirect disable pattern
- PortSwigger URL validation bypass cheat sheet (2024) — redirect-based bypass, DNS rebinding
- Python `urllib.parse` documentation — `urljoin` edge cases (trailing slash, protocol-relative URLs, fragments)
- Playwright memory issue tracker — context create/close cycle memory patterns
- Firecrawl and Crawl4AI path filter docs — cross-reference for fnmatch pattern semantics

### Tertiary (LOW confidence — general guidance)

- SSRF: Advanced Exploitation Guide (Intigriti) — TOCTOU DNS rebinding explanation
- CVE-2026-27127 (Craft CMS, GitLab Advisory Database) — real-world DNS rebinding SSRF bypass on `getaddrinfo`-then-request pattern (2026)
- Railway request timeout (60s default) — from Railway community; exact value for this service tier not verified in dashboard
- Playwright `max_redirects` default (20) — from Playwright docs

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH (direct codebase inspection, all patterns verified against `main.py`)
- SECURITY: HIGH (direct codebase inspection + OWASP + real-world CVE cross-reference)
- PITFALLS: HIGH (direct codebase inspection + crawlee pyproject.toml + Railway support confirmation)

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (crawlee releases may change version constraints; Railway timeout policy may change)
**Dimensions researched:** INTEGRATION, SECURITY, PITFALLS
