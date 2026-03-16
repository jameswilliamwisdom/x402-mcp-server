# Stack Research

**Domain:** x402 API Network — v2.0 Site Launch & Platform Polish
**Researched:** 2026-03-15
**Confidence:** HIGH

## Context

This is a subsequent milestone on an existing, working project. The v1.1 stack is locked in:

- **MCP server:** TypeScript, `@modelcontextprotocol/sdk ^1.11.0`, `viem ^2.0.0`, `x402-fetch ^1.1.0`, `zod ^4.3.6`
- **API backends:** Python/FastAPI on Railway (scraping, conversion, search, email) + home server (transcription)
- **Brand site:** Astro 5 + Starlight 0.37.x, static output, deployed via nginx on home server port 8888
- **Cloudflare Tunnel:** Locally managed config at `~/.cloudflared/config.yml`, tunnel ID `2223ce56-...`
- **Email:** Resend SDK `^2.x`, `resend>=2.0.0,<3.0.0` in requirements.txt
- **Scraping:** Playwright `1.44.0` (pinned) + trafilatura + beautifulsoup4 + lxml

This research covers ONLY the five new v2.0 features. Do not re-research the existing stack.

---

## Feature 1: Custom Domain + SSL for Brand Site

### Situation

The brand site runs at `http://10.0.0.2:8888` (local network only). The Cloudflare Tunnel already
exists and is locally managed (`~/.cloudflared/config.yml`). It currently routes several subdomains
(eth-bin-bot, btc-bin-bot, bot.jameswisdom.ink, etc.) and is launchd-managed for persistence.

### Solution: Add Public Hostname to Existing Cloudflare Tunnel

No new infrastructure is needed. Add one ingress entry to `~/.cloudflared/config.yml`:

```yaml
- hostname: x402.jameswisdom.ink   # or docs.jameswisdom.ink, etc.
  service: http://localhost:8888
```

Cloudflare terminates SSL automatically. The tunnel proxies HTTP from nginx to Cloudflare's HTTPS
edge. No certificate management required on the home server.

### What This Does NOT Require

| Approach | Verdict | Why Not |
|----------|---------|---------|
| Let's Encrypt / certbot | Not needed | Cloudflare handles TLS termination at its edge |
| nginx SSL config | Not needed | Tunnel sends HTTP to nginx; HTTPS is Cloudflare-side |
| New tunnel | Not needed | Existing tunnel supports multiple ingress rules |
| New cloudflared process | Not needed | Restart existing launchd service after config change |

### Supporting Technologies

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Cloudflare Tunnel (cloudflared) | Existing | Route public hostname to local nginx | Already in use for transcription API and crypto bots; zero-config SSL |
| nginx | Existing (home server) | Serve static Astro build from `/dist` | Already serving port 8888 |
| Astro | 5.x (existing) | Static site generator | Already built; no change needed for the site engine |

### Required Config Change

In `~/.cloudflared/config.yml`, add before the catch-all `http_status:404` rule:

```yaml
- hostname: x402.jameswisdom.ink
  service: http://localhost:8888
```

In Cloudflare DNS dashboard: the dashboard will auto-create a CNAME pointing
`x402.jameswisdom.ink` → `<tunnel-uuid>.cfargotunnel.com`. If using local-managed tunnel, create
this CNAME manually in Cloudflare DNS (proxied, not DNS-only).

### Astro Config Update Required

Update `SITE_URL` env var or hardcode in `astro.config.mjs`:

```javascript
site: 'https://x402.jameswisdom.ink',
```

This affects canonical URLs, sitemaps, and OG image URLs in the built output.

---

## Feature 2: DOCX→PDF Conversion

### Situation

The conversion API already has WeasyPrint (HTML→PDF) and Pillow (images). The previous STACK.md
recommended LibreOffice headless, noting it adds ~300MB to Docker. The v2.0 task is to research
lightweight alternatives to LibreOffice.

### The DOCX→PDF Problem

Pure-Python DOCX→PDF conversion with high fidelity does not exist. Every approach involves a
tradeoff between dependency size, fidelity, and runtime complexity. The candidates in order of
recommendation:

### Recommended: mammoth + WeasyPrint (two-step pipeline)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `mammoth` | `1.12.0` | DOCX → semantic HTML | Pure Python; 0 system dependencies; reads `.docx` ZIP structure directly; active (released March 12, 2026) |
| `weasyprint` | `>=68.1` (already installed) | HTML → PDF | Already in requirements.txt for HTML→PDF; no new dependency |

**Pipeline:** DOCX → mammoth → HTML → WeasyPrint → PDF

**Fidelity tradeoffs (known, confirmed from mammoth docs):**
- Text content: preserved
- Headings, bold, italic, lists, links, footnotes: preserved
- Table text content: preserved; table borders/styling: stripped
- Images: preserved inline as data URIs by default
- Complex Word formatting (columns, text boxes, floating elements): partially lost
- Custom Word styles: mappable via mammoth's style mapping API

**When this is acceptable:** Document content conversion (reports, articles, contracts where
structure > pixel-perfect layout). Not suitable for branded PDFs where exact Word visual layout
must be reproduced.

**Installation:**
```bash
pip install mammoth
# weasyprint is already installed
```

No Dockerfile changes. No system packages. Docker image stays small.

### Alternative: LibreOffice headless (NOT recommended for v2.0)

The previous research recommended this approach. It works and produces high-fidelity output, but
adds ~300MB to the Railway Docker image and ~5-15 second Railway cold-start penalty. Exclude from
v2.0 since mammoth + WeasyPrint is sufficient for the stated use case.

| Approach | Fidelity | Docker size cost | System deps | Verdict |
|----------|----------|-----------------|-------------|---------|
| mammoth + WeasyPrint | Medium (semantic) | 0 MB (already installed) | None | **Recommended** |
| LibreOffice headless | High (near-identical) | +300 MB | libreoffice apt package | Defer — overkill for v2.0 |
| docx2pdf | High (uses LibreOffice) | +300 MB + wrapper overhead | libreoffice apt package | Worse than bare LibreOffice |
| python-docx alone | Low (text only) | ~1 MB | None | Not suitable for PDF output |
| unoconv | High (uses LibreOffice) | +300 MB | libreoffice + Python 2 layer | Deprecated, do not use |

### Integration Pattern

```python
import mammoth
import weasyprint
import tempfile
import os

def docx_to_pdf(docx_bytes: bytes) -> bytes:
    """Convert DOCX bytes to PDF bytes via mammoth + WeasyPrint pipeline."""
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    html = result.value  # Semantic HTML string
    # Warnings in result.messages — log but don't fail on them

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        doc = weasyprint.HTML(string=html, url_fetcher=safe_url_fetcher)
        doc.write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()
```

The `safe_url_fetcher` is already defined in `x402-conversion-api/main.py` for SSRF protection.

### Discriminated Union Addition

Add a new type to `ConvertRequest` in `main.py`:

```python
class DocxConvertRequest(BaseModel):
    type: Literal["docx_pdf"]
    url: BoundedHttpUrl
```

No new Pydantic imports needed — Literal and BoundedHttpUrl are already used.

---

## Feature 3: Multi-Page Site Crawling

### Situation

The scraping API currently handles single-page scraping (POST /scrape). The new feature adds
multi-page crawling: given a start URL, crawl all pages within the same domain up to a depth/page
limit, return structured data per page.

### Recommended: crawlee with PlaywrightCrawler

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `crawlee[playwright]` | `1.5.0` (released March 6, 2026) | Multi-page crawling with Playwright | Built by Apify; `enqueue_links()` with same-domain strategy; `max_crawl_depth` built in; uses existing Playwright browser |

**Installation:**
```bash
pip install 'crawlee[playwright]'
# playwright already installed — no separate install needed
```

**Key API surface used:**

```python
from crawlee.playwright_crawler import PlaywrightCrawler

crawler = PlaywrightCrawler(
    max_crawl_depth=3,       # Stop enqueueing after depth 3
    max_requests_per_crawl=50,  # Hard cap on total pages
)

@crawler.router.default_handler
async def request_handler(context):
    await context.enqueue_links(strategy='same-domain')  # Same TLD + subdomains only
    page_html = await context.page.content()
    # ... extract_content() same as single-page scraper
```

**Why crawlee over rolling your own with Playwright + asyncio queue:**
- `enqueue_links(strategy='same-domain')` handles same-domain filtering automatically
- `max_crawl_depth` prevents infinite loops without manual depth tracking
- Request deduplication built in — same URL won't be crawled twice
- Memory-backed request queue — no Redis needed for this use case

### Important: Playwright Version Compatibility

The scraping API currently pins `playwright==1.44.0`. Crawlee 1.5.0 may require a more recent
Playwright. Verify compatibility before pinning — or unpin Playwright and let crawlee's dependency
resolution choose a compatible version.

**Action:** Check crawlee 1.5.0 `setup.cfg` / `pyproject.toml` for its playwright constraint.
If crawlee requires `playwright>=1.5x`, update the scraping API's pinned playwright version.

### SSRF Integration

The existing `validate_url_for_ssrf()` in `main.py` must be applied to every URL before
PlaywrightCrawler fetches it. Integrate via a `pre_navigation_hook`:

```python
@crawler.router.pre_navigation_hook
async def ssrf_hook(context):
    try:
        validate_url_for_ssrf(context.request.url)
    except ValueError as e:
        raise Exception(f"SSRF blocked: {e}")
```

Without this hook, the multi-page crawler would follow links to private IPs, bypassing the
existing SSRFMiddleware (which only validates the initial `/crawl` request body URL).

### New Endpoint Pattern

```
POST /crawl   — crawl a site (x402 payment: $0.05 suggested)
GET /crawl/test  — fixture response
```

Request model:
```python
class CrawlRequest(BaseModel):
    url: BoundedHttpUrl
    max_pages: int = Field(default=10, ge=1, le=50)
    max_depth: int = Field(default=3, ge=1, le=5)
```

Response: list of per-page extraction results (same schema as `/scrape` per page).

---

## Feature 4: Email Attachments + CC/BCC

### Situation

The email API currently sends `to`, `subject`, `body`, and optional `reply_to`. The Resend SDK
already supports attachments, CC, and BCC — this is a code-only change, no new libraries.

### Resend SDK Support (Confirmed from Official API Reference)

| Parameter | Type | Notes |
|-----------|------|-------|
| `cc` | `str \| list[str]` | Carbon copy recipients |
| `bcc` | `str \| list[str]` | Blind carbon copy recipients |
| `attachments` | `list[dict]` | Max 40MB total after base64 encoding |
| `attachments[].filename` | `str` | Attachment display name |
| `attachments[].content` | `buffer \| str` | File content as bytes buffer or base64 string |
| `attachments[].path` | `str` | Hosted URL — Resend fetches it server-side |
| `attachments[].content_type` | `str` | MIME type (optional) |

**Resend SDK version:** `2.23.0` (current, Feb 23, 2026). Already in requirements.txt as
`resend>=2.0.0,<3.0.0`. No version change needed.

### No New Libraries

| What | Needed | Why |
|------|--------|-----|
| New Python package | No | Resend SDK 2.x already supports all fields |
| Requirements.txt change | No | Version constraint already covers 2.23.0 |
| New Railway deploy | No | Code-only change to existing email API |

### Pydantic Model Addition

```python
from typing import List, Optional, Union

class EmailAttachment(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., description="Base64-encoded file content")
    content_type: Optional[str] = Field(None, description="MIME type e.g. application/pdf")

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1, max_length=102400)
    reply_to: Optional[EmailStr] = None
    cc: Optional[Union[EmailStr, List[EmailStr]]] = None    # NEW
    bcc: Optional[Union[EmailStr, List[EmailStr]]] = None   # NEW
    attachments: Optional[List[EmailAttachment]] = None     # NEW
```

### Security Note

Accept attachments as base64 content strings (not file paths or URLs). This avoids:
1. SSRF via attachment URL fetch (no outbound fetch from user-supplied URLs)
2. File system access (no server-side paths exposed)
3. Content-type spoofing risk is caller's responsibility

Enforce max attachment total size (40MB Resend limit) and count (e.g., max 5 attachments per send).

---

## Feature 5: Astro + Starlight Docs Expansion

### Situation

The brand site has docs for the original 3 APIs (screenshot, PDF, crypto sentiment) plus Getting
Started and Wallet Setup. Need to add docs pages for 5 new v1.1 APIs: scraping, conversion, search,
email, transcription. This is a content addition — no new technology is needed.

### Current Versions (Verified)

| Package | Current in package.json | Latest on npm | Action |
|---------|------------------------|---------------|--------|
| `@astrojs/starlight` | `^0.37.7` | `0.37.6` (2 days ago) | Already current — `^0.37.7` resolves to latest |
| `astro` | `^5.18.0` | Check lockfile | Already on Astro 5 |

**No version updates needed.** The `^` ranges in package.json already pull the latest compatible
releases.

### Sidebar Config Addition

The current sidebar in `astro.config.mjs` has 3 items. After adding 5 API doc pages, restructure:

```javascript
sidebar: [
  { label: 'Getting Started', items: [
    { slug: 'getting-started' },
    { slug: 'wallet-setup' },
  ]},
  { label: 'APIs', items: [
    { slug: 'api-reference' },          // existing overview
    { slug: 'api-scraping' },           // NEW
    { slug: 'api-conversion' },         // NEW
    { slug: 'api-search' },             // NEW
    { slug: 'api-email' },              // NEW
    { slug: 'api-transcription' },      // NEW
  ]},
],
```

No Astro or Starlight config API changes — this is Starlight's standard sidebar array structure
(unchanged in 0.37.x).

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LibreOffice headless for DOCX→PDF | +300MB Docker image; Railway cold start penalty; overkill for v2.0 | mammoth + WeasyPrint (already installed) |
| unoconv | Deprecated Python 2 wrapper around LibreOffice; version mismatch errors | mammoth + WeasyPrint |
| docx2pdf | Just wraps LibreOffice on Linux; adds abstraction without benefit | mammoth directly |
| Let's Encrypt / certbot on home server | No need — Cloudflare Tunnel handles TLS at edge | Cloudflare Tunnel ingress rule |
| New Cloudflare Tunnel | Existing tunnel already works; adding ingress rules is simpler | Edit `~/.cloudflared/config.yml` |
| Scrapy for crawling | Heavy framework; requires Scrapy project structure; overkill for a single API endpoint | crawlee `PlaywrightCrawler` |
| BeautifulSoup alone for crawling | No built-in link queue, deduplication, or depth tracking | crawlee `PlaywrightCrawler` |
| Accepting attachment file paths or URLs | SSRF and file access risks | Base64 content strings only |
| Playwright MCP version in requirements.txt | Version-pinning may conflict with crawlee's playwright dep | Use `>=` constraint or let crawlee manage it |

---

## Installation Summary (New Packages Only)

### x402-scraping-api/requirements.txt additions

```
crawlee[playwright]>=1.5.0
```

Note: `playwright==1.44.0` may need to be relaxed to `playwright>=1.44.0` depending on crawlee's
internal constraint. Verify against crawlee's setup before pinning.

### x402-conversion-api/requirements.txt additions

```
mammoth>=1.12.0
```

WeasyPrint is already installed. No Dockerfile changes.

### x402-email-api/requirements.txt

No changes. `resend>=2.0.0,<3.0.0` already covers 2.23.0.

### Site (npm)

No changes. `@astrojs/starlight ^0.37.7` and `astro ^5.18.0` are already current.

### Infrastructure (no packages)

- Edit `~/.cloudflared/config.yml`: add 1 ingress rule
- Add DNS CNAME in Cloudflare dashboard
- Update `SITE_URL` env var / `astro.config.mjs`
- Restart cloudflared launchd service

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `mammoth>=1.12.0` | Python >=3.7, WeasyPrint >=68.1 | No known conflicts; pure Python XML parser |
| `crawlee[playwright]>=1.5.0` | Python >=3.9 | Requires playwright; verify crawlee's minimum playwright version vs pinned `==1.44.0` |
| `resend>=2.0.0,<3.0.0` | Python >=3.7 | SDK 2.23.0 is current; attachment content must be bytes or base64 string (not file path) |
| `@astrojs/starlight ^0.37.7` | astro ^5.18.0 | No breaking changes in 0.37.x minor range |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| mammoth + WeasyPrint | LibreOffice headless | When document pixel-fidelity is required (branded PDF reports, complex layouts with columns/text boxes) |
| crawlee PlaywrightCrawler | Custom asyncio queue | When you have very specific crawl behavior not covered by crawlee's API — unlikely for this use case |
| Cloudflare Tunnel ingress rule | New Cloudflare Pages deploy | When you want a fully managed CDN with edge caching; adds deployment complexity vs. existing tunnel |
| Base64 attachment content | Attachment URL fetch | When file size limit is not a concern and you want callers to avoid base64 overhead — not recommended due to SSRF risk |

---

## Sources

- [pypi.org/project/crawlee](https://pypi.org/project/crawlee/) — v1.5.0, March 6, 2026; `pip install 'crawlee[playwright]'` confirmed
- [crawlee.dev/python/docs/examples/playwright-crawler](https://crawlee.dev/python/docs/examples/playwright-crawler) — PlaywrightCrawler example, enqueue_links, same-domain strategy
- [crawlee.dev/python/api/class/EnqueueLinksFunction](https://crawlee.dev/python/api/class/EnqueueLinksFunction) — strategy parameter, max_crawl_depth on crawler class
- [pypi.org/project/mammoth](https://pypi.org/project/mammoth/) — v1.12.0, March 12, 2026; Python >=3.7; tables/images supported; table borders stripped
- [github.com/mwilliamson/python-mammoth](https://github.com/mwilliamson/python-mammoth) — limitations confirmed: formatting ignored, semantic structure preserved
- [resend.com/docs/api-reference/emails/send-email](https://resend.com/docs/api-reference/emails/send-email) — attachments (content: buffer|string, filename, path, content_type, content_id); cc/bcc: string|string[]; 40MB max
- [github.com/resend/resend-python](https://github.com/resend/resend-python) — v2.23.0, Feb 23, 2026; cc/bcc/attachments confirmed in README examples
- [developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/) — CNAME auto-created; SSL handled by Cloudflare edge; multiple ingress rules on single tunnel
- [npmjs.com/package/@astrojs/starlight](https://www.npmjs.com/package/@astrojs/starlight) — 0.37.6 latest (2 days ago); already at current version

---
*Stack research for: x402 API Network — v2.0 Site Launch & Platform Polish*
*Researched: 2026-03-15*
