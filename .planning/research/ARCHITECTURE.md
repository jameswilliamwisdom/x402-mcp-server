# Architecture Research

**Domain:** x402 API Network v2.0 — Site Launch & Platform Polish
**Researched:** 2026-03-15
**Confidence:** HIGH (all key integration points verified against live source code and official docs)

## Standard Architecture

### System Overview (v2.0 additions highlighted)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP Client (Claude Desktop, etc.)                   │
│              npx -y x402-mcp-server  |  X402_PRIVATE_KEY env var             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ stdio / MCP protocol
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                        x402 MCP Server (src/index.ts)                        │
│                 TypeScript, @modelcontextprotocol/sdk, x402-fetch             │
│                                                                               │
│  EXISTING TOOLS (v1.1)            MODIFIED TOOLS (v2.0)                      │
│  ─────────────────────────        ─────────────────────────────────────      │
│  x402_network_info (free)         x402_scrape_url  → +crawl param            │
│  x402_screenshot (free+paid)      x402_send_email  → +cc/bcc/attachments     │
│  x402_pdf_extract (free+paid)     x402_convert_file → +docx type             │
│  x402_sentiment / market /                                                   │
│    intelligence (free+paid)                                                  │
│  x402_web_search (free+paid)                                                 │
│  x402_transcribe_audio (free+paid)                                           │
└──────────────┬──────────────────────────────────────────────────────────────┘
               │ HTTP via x402-fetch
               │
     ┌─────────┴───────────────────────────────────────────────────────────────┐
     │                     API Layer (existing Railway + home server)           │
     │                                                                          │
     │  Railway ──────────────────────────────────────────────────────────     │
     │  Scraping API   → add POST /crawl endpoint (new)                        │
     │  Conversion API → add "docx" type to discriminated union (modified)     │
     │  Email API      → add cc/bcc/attachments to EmailRequest (modified)     │
     │  Search API     → unchanged for v2.0                                    │
     │                                                                          │
     │  Home Server ──────────────────────────────────────────────────────     │
     │  Transcription API (transcribe.jameswisdom.ink) → unchanged v2.0       │
     │  Brand Site (nginx :8888) → domain + SSL added (see below)             │
     └──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        Brand Site (v2.0: PUBLIC via HTTPS)                   │
│                                                                               │
│  BEFORE v2.0:                      AFTER v2.0:                               │
│  Astro + Starlight static site     Same static build                        │
│  nginx on port 8888                nginx on port 8888 (unchanged)           │
│  HTTP only                         Cloudflare Tunnel → HTTPS + custom domain│
│  Local network only (10.0.0.2)     Public internet accessible               │
│  site: 'https://x402.todo'         site: 'https://x402.jameswisdom.ink'     │
│                                    (or chosen subdomain)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | v2.0 Change |
|-----------|----------------|-------------|
| `src/index.ts` | MCP server — 11 tools, routes free/paid | Modify `x402_scrape_url`, `x402_send_email`, `x402_convert_file` tool handlers for new params |
| Scraping API (`x402-scraping-api/main.py`) | URL → structured JSON via Playwright | Add `POST /crawl` endpoint, new `CrawlRequest` model |
| Email API (`x402-email-api/main.py`) | Transactional email via Resend | Add `cc`, `bcc`, `attachments` to `EmailRequest` model and `build_send_params()` |
| Conversion API (`x402-conversion-api/main.py`) | File format conversion | Add `DocxConvertRequest` to `ConvertRequest` union, add `sync_docx_to_pdf()` function |
| Brand site (`site/`) | Marketing + docs | Update `astro.config.mjs` SITE_URL, add 5 new API docs pages, sidebar entries |
| nginx (`/usr/local/etc/nginx/` on macOS) | Reverse proxy for site + transcription | Add SSL config or rely entirely on Cloudflare Tunnel (see below) |
| Cloudflare Tunnel | Public HTTPS exposure of brand site | New — `cloudflared` config routes custom domain to `http://localhost:8888` |

---

## New vs Modified Components

### Modified (existing files change)

| File | What Changes | Notes |
|------|-------------|-------|
| `x402-scraping-api/main.py` | Add `CrawlRequest` model, `POST /crawl` route, `crawl_site()` function | Same Playwright browser, new endpoint |
| `x402-email-api/main.py` | Add `cc`, `bcc`, `attachments` to `EmailRequest`, update `build_send_params()` | Resend SDK already supports these — purely additive |
| `x402-conversion-api/main.py` | Add `DocxConvertRequest` to union, add `sync_docx_to_pdf()`, update `requirements.txt` | `mammoth` + `weasyprint` (already installed) chain |
| `x402-conversion-api/requirements.txt` | Add `mammoth>=1.8.0` | `weasyprint` already present |
| `x402-conversion-api/Dockerfile` | Add mammoth install — no new system deps needed | mammoth is pure Python |
| `src/index.ts` | Add `crawl_url` param to `x402_scrape_url`, add `cc/bcc/attachments` to `x402_send_email`, add `docx` to `x402_convert_file` type enum | Zod schemas updated |
| `site/astro.config.mjs` | Set `SITE_URL` env var at build time to real public domain | Build script change |
| `site/src/content/docs/api-reference.mdx` | Add all v1.1 tools (scraping, conversion, search, email, transcription) | Currently only 6 tools documented |
| Cloudflare Tunnel config | New `~/.cloudflared/config.yml` routing domain → `http://localhost:8888` | No nginx changes required |

### New (net new files)

| Component | Location | What It Is |
|-----------|----------|------------|
| Crawl fixture | `x402-scraping-api/fixture_crawl.json` | Free test fixture for `GET /crawl/test` |
| Cloudflare Tunnel config | `~/.cloudflared/config.yml` | Routes public hostname to local nginx |
| Cloudflare launchd plist | `~/Library/LaunchAgents/com.cloudflare.cloudflared.plist` | Keeps tunnel alive (or managed by `cloudflared service install`) |
| New docs pages | `site/src/content/docs/api-scraping.mdx`, `api-email.mdx`, `api-conversion.mdx`, `api-search.mdx`, `api-transcription.mdx` | Separate pages per API or extended api-reference.mdx |

---

## Architectural Patterns

### Pattern 1: Crawl Feature — New Endpoint on Existing Scraping Service

**What:** Add `POST /crawl` as a new endpoint to the existing `x402-scraping-api` service. It accepts a seed URL, max depth, and max pages, then BFS-crawls the site and returns an array of scrape results. The existing Playwright browser singleton and `scrape_page()` / `extract_content()` functions are reused.

**Why new endpoint, not parameter:** The crawl operation returns a different response schema (`results: [ScrapeResult]` array vs single result), has different limits, and warrants a different price point ($0.05+ vs $0.02). A separate endpoint is cleaner than overloading `/scrape` with a boolean flag that changes the return type.

**Trade-offs:**
- Pro: reuses existing Playwright browser singleton — no new browser lifecycle management
- Pro: SSRF validation already in `validate_url_for_ssrf()` — call it on each discovered URL before queuing
- Con: Crawl is inherently slow (N pages * ~2s each). Railway timeout limit is a concern — set max_pages default conservatively (10–15 pages)
- Con: Each page costs Railway compute. Price must reflect N-page cost, not just 1-page cost.

**Crawl implementation pattern:**

```python
from collections import deque
from urllib.parse import urljoin, urlparse

class CrawlRequest(BaseModel):
    url: BoundedHttpUrl = Field(..., description="Seed URL to start crawl from")
    max_pages: int = Field(10, ge=1, le=30,
                           description="Max pages to crawl (default 10, max 30)")
    max_depth: int = Field(2, ge=1, le=3,
                           description="Max link-follow depth from seed (default 2, max 3)")
    same_domain_only: bool = Field(True,
                                   description="Only follow links on same domain (default true)")

@app.post("/crawl")
@pay("$0.05")  # Higher price — N page loads
async def crawl(request: Request, body: CrawlRequest):
    seed = str(body.url)
    seed_domain = urlparse(seed).netloc

    queue = deque([(seed, 0)])  # (url, depth)
    visited = set()
    results = []

    while queue and len(visited) < body.max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        try:
            validate_url_for_ssrf(url)  # SSRF check on every discovered URL
        except ValueError:
            continue
        visited.add(url)

        page_result = await scrape_page(url, wait_for=None)
        extracted = extract_content(page_result["html"], url)
        results.append({"url": url, "depth": depth, **extracted})

        # Enqueue links if not at max depth
        if depth < body.max_depth:
            for link in extracted.get("links", []):
                href = link["url"]
                if body.same_domain_only and urlparse(href).netloc != seed_domain:
                    continue
                if href not in visited:
                    queue.append((href, depth + 1))

    return {"success": True, "seed": seed, "pages_crawled": len(results), "results": results}
```

**MCP server changes for crawl** — modify `x402_scrape_url` or add new `x402_crawl_site` tool. New tool is cleaner:

```typescript
server.tool(
  "x402_crawl_site",
  `Crawl a website starting from a seed URL and return structured content for all discovered pages.
Price: $0.05 USDC per crawl (up to 10 pages) | Free test: returns fixture data.

Follows links breadth-first within the same domain. Returns array of scrape results.
Without X402_PRIVATE_KEY, only the free test endpoint is available.`,
  {
    url: z.string().url().describe("Seed URL to start crawl from"),
    max_pages: z.number().int().min(1).max(30).default(10)
      .describe("Max pages to crawl (default: 10, max: 30)"),
    max_depth: z.number().int().min(1).max(3).default(2)
      .describe("Max link-follow depth from seed (default: 2)"),
    same_domain_only: z.boolean().default(true)
      .describe("Only follow links within the same domain (default: true)"),
  },
  async (params) => {
    const base = APIS.scraping.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const data = await apiPost(base, "/crawl", { ...params }, true);
        return textResult({ mode: "paid", cost: "$0.05", ...data });
      } else {
        const data = await apiGet(base, "/crawl/test");
        return textResult({ mode: "free_test", ...data });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

**Decision:** New `x402_crawl_site` tool (12th tool) — don't add a `crawl` parameter to the existing `x402_scrape_url`. Different schema, different price, different use case.

---

### Pattern 2: Email Attachments + CC/BCC — Extend Existing Endpoint

**What:** Add `cc`, `bcc`, and `attachments` fields to the existing `EmailRequest` Pydantic model and `POST /send` endpoint. The Resend SDK already supports all three — this is a purely additive model change, not a new endpoint.

**Why same endpoint:** The operation is still "send one email" — it just has more headers/attachments. The response schema (`{message_id}`) is unchanged. Same `@pay("$0.01")` decorator applies.

**Resend SDK attachment format** (verified against official API reference):
- `attachments` field: list of objects with `content` (bytes or base64 string), `filename` (string), and optionally `content_type` (MIME type, auto-derived if omitted)
- `content` can be a Python `bytes` object or base64-encoded string
- For file attachments from URL: use `path` key instead of `content` — Resend fetches the file server-side
- Max total email size: 40MB after Base64 encoding
- `cc` and `bcc`: `str | list[str]` — same format as `to`

**Email API changes:**

```python
# Updated EmailRequest model
class AttachmentItem(BaseModel):
    filename: str = Field(..., description="Attachment filename (e.g. 'report.pdf')")
    path: Optional[str] = Field(None, description="URL to fetch file from (Resend fetches server-side)")
    content: Optional[str] = Field(None, description="Base64-encoded file content (alternative to path)")
    content_type: Optional[str] = Field(None, description="MIME type (auto-derived if omitted)")

class EmailRequest(BaseModel):
    to: EmailStr = Field(...)
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1, max_length=102400)
    reply_to: Optional[EmailStr] = Field(None)
    cc: Optional[Union[EmailStr, List[EmailStr]]] = Field(None,
        description="CC recipients (single address or list)")
    bcc: Optional[Union[EmailStr, List[EmailStr]]] = Field(None,
        description="BCC recipients (single address or list)")
    attachments: Optional[List[AttachmentItem]] = Field(None, max_length=10,
        description="File attachments (max 10). Use 'path' for URL-hosted files or 'content' for base64.")

def build_send_params(body: EmailRequest) -> dict:
    # ... existing logic ...
    if body.cc:
        params["cc"] = [str(body.cc)] if isinstance(body.cc, str) else [str(a) for a in body.cc]
    if body.bcc:
        params["bcc"] = [str(body.bcc)] if isinstance(body.bcc, str) else [str(a) for a in body.bcc]
    if body.attachments:
        params["attachments"] = [
            {k: v for k, v in att.model_dump().items() if v is not None}
            for att in body.attachments
        ]
    return params
```

**MCP server changes** — update `x402_send_email` Zod schema:

```typescript
// Add to existing x402_send_email tool params
cc: z.union([z.string().email(), z.array(z.string().email())]).optional()
  .describe("CC recipients (single address or array)"),
bcc: z.union([z.string().email(), z.array(z.string().email())]).optional()
  .describe("BCC recipients (single address or array)"),
attachments: z.array(z.object({
  filename: z.string().describe("Attachment filename"),
  path: z.string().url().optional().describe("URL to hosted file (Resend fetches it)"),
  content: z.string().optional().describe("Base64-encoded file content"),
  content_type: z.string().optional().describe("MIME type (auto-derived if omitted)"),
})).max(10).optional().describe("File attachments (max 10)"),
```

**Rate limiting consideration:** Attachments with `path` URLs cause Resend to fetch external URLs server-side — SSRF risk. But Resend does this on their servers, not ours. The email API has no outbound URL fetching from our code today (intentionally — noted in `main.py` line 244). The `path` field delegates fetching to Resend's servers, which is acceptable. If we want to avoid delegating this to Resend, use `content` (base64) only and reject `path` attachments. Recommendation: support both but note the distinction in docs.

**Decision:** Extend existing `POST /send` and `x402_send_email` tool. No new endpoint needed.

---

### Pattern 3: DOCX-to-PDF — Extend Existing Conversion Service

**What:** Add a `"docx"` type to the existing `ConvertRequest` discriminated union in the conversion API. No new Railway service needed — the conversion API is the right home for this.

**Why same service:** DOCX→PDF is semantically identical to HTML→PDF already in the service. Both are document-to-PDF conversions. The service already has WeasyPrint installed, and mammoth (the DOCX→HTML step) is pure Python with zero system dependencies — no new apt packages needed.

**Conversion chain:** `DOCX → HTML (mammoth) → PDF (WeasyPrint)` — both already present or trivially addable.

**Mammoth limitations** (verified — important for docs):
- Produces clean, semantic HTML from semantic DOCX structure
- Complex tables: borders/shading ignored, cell content preserved
- Images: inline base64 by default — may cause large output for image-heavy docs
- Complex layouts (multi-column, text boxes, floating elements): not supported
- Best for: reports, letters, text-heavy documents
- Not suitable for: pixel-perfect layout preservation, complex Word templates

**Dockerfile impact:** Mammoth is pure Python — no new `apt-get` deps. Add to `requirements.txt` only.

```python
# requirements.txt addition
mammoth>=1.8.0

# main.py addition
import mammoth

class DocxConvertRequest(BaseModel):
    type: Literal["docx"]
    url: BoundedHttpUrl

ConvertRequest = Annotated[
    Union[ImageConvertRequest, CsvConvertRequest, HtmlConvertRequest, DocxConvertRequest],
    Field(discriminator="type"),
]

def sync_docx_to_pdf(file_bytes: bytes, source_url: str) -> bytes:
    """Convert DOCX bytes to PDF via mammoth (DOCX→HTML) + WeasyPrint (HTML→PDF).

    Sync — must be called via run_in_threadpool.
    Uses safe_url_fetcher for SSRF protection on WeasyPrint secondary fetches.
    """
    # Step 1: DOCX → HTML
    result = mammoth.convert_to_html(BytesIO(file_bytes))
    html_string = result.value  # Clean, semantic HTML

    # Step 2: HTML → PDF (reuse existing WeasyPrint pattern)
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        doc = weasyprint.HTML(
            string=html_string,
            base_url=source_url,
            url_fetcher=safe_url_fetcher,
        )
        doc.write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()

# In convert() handler — add to dispatch block:
elif body.type == "docx":
    output_bytes = await run_in_threadpool(sync_docx_to_pdf, file_bytes, source_url)
    mime_type = "application/pdf"
```

**MCP server changes** — update `x402_convert_file` type enum:

```typescript
type: z.enum(["image", "csv", "html_pdf", "docx"])
  .describe("Conversion type: image, csv, html_pdf, or docx (DOCX to PDF)")
```

**Decision:** Extend existing `/convert` endpoint and `x402_convert_file` tool. No new service or endpoint. Deploy triggers a Railway redeploy of the conversion service.

---

### Pattern 4: Custom Domain + SSL — Cloudflare Tunnel (Recommended)

**What:** The brand site is currently served by nginx on port 8888, local network only, HTTP. To make it public with HTTPS and a custom domain, use a second Cloudflare Tunnel — the same mechanism already proven for the transcription API (`transcribe.jameswisdom.ink`).

**Why Cloudflare Tunnel over Let's Encrypt + nginx SSL:**
- No router config or port-forwarding required (macOS Monterey, home network)
- No static IP required — tunnel re-establishes on reconnect
- SSL is fully automatic — Cloudflare manages certificates
- Already proven: the transcription tunnel is working with a custom subdomain
- AdGuard Home occupies port 80 — Let's Encrypt HTTP-01 challenge would fail without workaround
- Replicates existing pattern exactly — no new tools or skills needed

**Why not Let's Encrypt DNS-01:** Requires Cloudflare API token + certbot `dns-cloudflare` plugin. Works fine but adds complexity for macOS cert renewal. The Cloudflare Tunnel approach is simpler and already working.

**Config structure:**

The transcription service already uses a tunnel. The brand site tunnel can either:
1. **Separate tunnel** — new `cloudflared` config, new CNAME in Cloudflare DNS. Cleanest separation.
2. **Same tunnel, additional public hostname** — Cloudflare Tunnels support multiple public hostnames per tunnel. One `cloudflared` process handles both `x402.jameswisdom.ink → localhost:8888` and `transcribe.jameswisdom.ink → localhost:PORT`. More efficient but couples two services.

**Recommendation: single tunnel, two hostnames.** The transcription tunnel is already running via launchd. Add the brand site as a second hostname in the same config:

```yaml
# ~/.cloudflared/config.yml (extend existing or create if not present)
tunnel: <existing-tunnel-uuid>
credentials-file: ~/.cloudflared/<uuid>.json

ingress:
  - hostname: x402.jameswisdom.ink
    service: http://localhost:8888
  - hostname: transcribe.jameswisdom.ink
    service: http://localhost:<transcription-port>
  - service: http_status:404
```

**DNS change:** Add CNAME `x402` → `<tunnel-uuid>.cfargotunnel.com` in Cloudflare DNS panel. Cloudflare auto-manages HTTPS for the domain.

**nginx changes:** None required. nginx keeps serving on port 8888 as-is. The Cloudflare Tunnel terminates TLS at Cloudflare's edge and forwards plain HTTP to `localhost:8888`. No SSL config needed in nginx.

**Brand site build changes:** Update `SITE_URL` env var before build:

```bash
# In build script or before astro build
SITE_URL=https://x402.jameswisdom.ink npm run build
```

The `astro.config.mjs` already uses `process.env.SITE_URL || 'https://x402.todo'` — no code change needed, just correct env var at build time.

**Sidebar navigation update:** The `site/astro.config.mjs` sidebar currently only has Getting Started (2 pages) and Reference (1 page, api-reference). Add documentation for all 5 v1.1 APIs. Two options:

Option A: Add all APIs to the existing `api-reference.mdx` (simpler, single page update).
Option B: Create separate pages per API, add to sidebar (better for SEO and deep linking).

**Recommendation: Option A** for v2.0 — update `api-reference.mdx` in place. Avoids sidebar restructuring and is faster to ship. Separate pages can be split in a future milestone.

---

## Data Flow

### Crawl Request Flow

```
MCP Client calls x402_crawl_site({ url: "https://docs.example.com", max_pages: 15 })
    │
src/index.ts → apiPost(base, "/crawl", { url, max_pages, max_depth, same_domain_only }, true)
    │
x402-fetch → POST https://x402-scraping-api-production.up.railway.app/crawl
    │
fastapi-x402 → 402 → x402-fetch signs payment → retry with X-Payment header
    │
crawl() handler: BFS queue starting from seed URL
    │  For each URL in queue:
    │    1. validate_url_for_ssrf(url)  — blocks private IPs
    │    2. scrape_page(url, wait_for=None)  — reuses existing Playwright scraper
    │    3. extract_content(html, url)  — reuses existing extraction pipeline
    │    4. Append to results
    │    5. Enqueue discovered links (if same_domain and depth < max_depth)
    │
JSON: { success, seed, pages_crawled, results: [...ScrapeResult] }
    │
textResult → MCP client
```

### Email with Attachments Flow

```
MCP Client calls x402_send_email({ to, subject, body, cc: [...], attachments: [{path: url}] })
    │
src/index.ts → apiPost(base, "/send", { to, subject, body, cc, attachments }, true)
    │
x402-fetch → POST /send with X-Payment header
    │
send_email() handler:
    │    check_and_increment_wallet_limit(wallet)
    │    check_and_increment_domain_limit(wallet, to)
    │    build_send_params() → includes cc, bcc, attachments in Resend params
    │    _do_send() → resend.Emails.send(params)
    │    Resend API: fetches attachment URLs server-side if using "path" key
    │
{ message_id } → textResult → MCP client
```

### DOCX Conversion Flow

```
MCP Client calls x402_convert_file({ url: "https://.../file.docx", type: "docx" })
    │
src/index.ts → apiPost(base, "/convert", { url, type: "docx" }, true)
    │
convert() handler:
    │    1. download_file(url) → bytes (10MB limit, SSRF validated, streaming)
    │    2. run_in_threadpool(sync_docx_to_pdf, file_bytes, source_url)
    │       ├── mammoth.convert_to_html(BytesIO(file_bytes)) → HTML string
    │       └── weasyprint.HTML(string=html, url_fetcher=safe_url_fetcher).write_pdf()
    │    3. output size guard (8MB limit)
    │    4. base64.b64encode(pdf_bytes)
    │
{ success, type: "docx", mime_type: "application/pdf", data: "<base64>" }
    │
textResult → MCP client
```

### Brand Site Request Flow (after v2.0)

```
Public user visits https://x402.jameswisdom.ink
    │
DNS: x402.jameswisdom.ink CNAME → <tunnel-uuid>.cfargotunnel.com
    │
Cloudflare edge: TLS termination (auto-managed cert)
    │
Cloudflare Tunnel: encrypted tunnel to cloudflared process on home server
    │
cloudflared → http://localhost:8888 (nginx)
    │
nginx: serves Astro static files from /dist
    │
HTML/JS/CSS → Cloudflare → user's browser (HTTPS throughout)
```

---

## Recommended Project Structure

### v2.0 Additions to Existing Services

```
x402-scraping-api/
├── main.py           # + CrawlRequest model, crawl() endpoint, crawl_site() function
├── fixture.json      # existing single-page fixture (unchanged)
└── fixture_crawl.json  # NEW: multi-page crawl fixture for /crawl/test

x402-email-api/
└── main.py           # + cc, bcc, attachments to EmailRequest and build_send_params()

x402-conversion-api/
├── main.py           # + DocxConvertRequest, sync_docx_to_pdf()
└── requirements.txt  # + mammoth>=1.8.0

src/
└── index.ts          # + x402_crawl_site tool, update x402_send_email, x402_convert_file

site/src/content/docs/
└── api-reference.mdx  # Add v1.1 API docs (all 5 APIs currently missing)

~/.cloudflared/
└── config.yml        # Add x402.jameswisdom.ink → localhost:8888 ingress rule
```

---

## Integration Points

### External Services

| Service | Integration Pattern | v2.0 Change | Notes |
|---------|---------------------|-------------|-------|
| Resend API | Python `resend` SDK in email service | Add cc, bcc, attachments to SDK params | SDK already supports all three — zero new dependencies |
| Cloudflare Tunnel | `cloudflared` daemon, config.yml | New ingress rule for brand site | Already proven for transcription service |
| Cloudflare DNS | CNAME record | Add CNAME for site subdomain | Managed in Cloudflare dashboard |
| Railway (scraping) | FastAPI + fastapi-x402 | New `/crawl` endpoint | Same service, redeploy |
| Railway (conversion) | FastAPI + fastapi-x402 | New "docx" type in union | Same service, redeploy — no new apt deps |

### Internal Boundaries

| Boundary | Communication | v2.0 Notes |
|----------|---------------|------------|
| MCP server ↔ Scraping API | HTTP via x402-fetch | Add `POST /crawl` call path for new `x402_crawl_site` tool |
| MCP server ↔ Email API | HTTP via x402-fetch | Forward cc, bcc, attachments params in payload |
| MCP server ↔ Conversion API | HTTP via x402-fetch | Add "docx" to type enum in Zod schema and payload |
| cloudflared ↔ nginx | `http://localhost:8888` | No nginx config change — tunnel routes to existing nginx |
| Crawl handler ↔ scrape_page() | Direct Python call (same module) | BFS loop calls existing scrape function N times |
| sync_docx_to_pdf() ↔ weasyprint | In-process, threadpool | Same pattern as sync_html_to_pdf() already in conversion API |

---

## Build Order

Dependencies between v2.0 features:

```
[1] Brand site docs update (no external deps)
        │
        ↓
[2] Custom domain + SSL (depends on: knowing final domain URL for astro SITE_URL)
        │
        ↓ (site is public — can share URLs)
[3a] Crawl endpoint (no external deps, standalone Railway redeploy)
[3b] Email attachments (no external deps, standalone Railway redeploy)
[3c] DOCX→PDF (no external deps, standalone Railway redeploy)
        │
        ↓ (all backends done)
[4] MCP server update (src/index.ts) — add crawl tool, update email+convert schemas
        │
        ↓
[5] npm publish v2.0.0
```

**Recommended build sequence with rationale:**

**Step 1: Brand site docs** — Write first because it's pure content work (no backend changes) and can be done in parallel with anything. Updating `api-reference.mdx` with all 5 v1.1 APIs is straightforward copy/adapt from existing 6 tools. No deploys needed.

**Step 2: Custom domain + SSL** — Do before building new features because the brand site URL (`SITE_URL`) must be set correctly in `astro.config.mjs` for OG tags and canonical URLs. Once the domain is live, rebuild and redeploy site. Cloudflare Tunnel config change takes ~5 minutes.

**Step 3a: DOCX→PDF** — Build first among backend features because it has the cleanest scope: one new model class, one new function, one new `elif` branch. No new system dependencies (mammoth is pure Python). Validates Railway redeploy works before touching scraping/email.

**Step 3b: Email attachments** — Build second among backends. Purely additive Pydantic model change. The only new complexity is the Resend `attachments` parameter format — already confirmed against the Resend API reference.

**Step 3c: Crawl endpoint** — Build last among backends because it's the most complex (stateful BFS loop, timeout risks, Railway cold start timing). By the time this is built, the DOCX and email deploys have validated Railway deploy cycle is working.

**Step 4: MCP server update** — After all three Railway backends are deployed with new endpoints/capabilities. Add `x402_crawl_site` tool, update `x402_send_email` and `x402_convert_file` Zod schemas.

**Step 5: npm publish** — After integration test in both free and paid modes.

**Parallel work possible:** Steps 1, 3a, 3b, 3c can all be developed simultaneously (separate files, separate services). The only hard sequencing is: domain before site rebuild, backends before MCP update, MCP update before npm publish.

---

## Anti-Patterns

### Anti-Pattern 1: Crawl as Parameter on /scrape

**What people do:** Add a `crawl=true` boolean to `POST /scrape` to avoid a new endpoint.

**Why it's wrong:** The response schema changes completely (single result vs array). The price should be different (N page loads). Putting both behaviors in one endpoint with a boolean flag violates single-responsibility and makes the API contract ambiguous.

**Do this instead:** New `POST /crawl` endpoint with its own request model and `@pay("$0.05")` decorator. Reuses existing `scrape_page()` and `extract_content()` — just orchestrates them in a BFS loop.

### Anti-Pattern 2: DOCX Conversion in a New Railway Service

**What people do:** Create a new `x402-docx-api` service because DOCX conversion feels like a separate concern.

**Why it's wrong:** Mammoth is pure Python (no system deps). WeasyPrint is already installed in the conversion service. The conversion service is the right home for all file format transformations — that's its stated purpose. A new service adds Railway billing, a new Dockerfile, and a new URL to manage for a feature that adds ~30 lines to an existing service.

**Do this instead:** Add `"docx"` as a new type in the existing `ConvertRequest` discriminated union. One `requirements.txt` addition (`mammoth`), one new function, one new `elif` branch.

### Anti-Pattern 3: Let's Encrypt on Home Server (Port 80 Conflict)

**What people do:** Install certbot, configure nginx for SSL, fight with port 80 being occupied by AdGuard Home.

**Why it's wrong:** AdGuard Home is already on port 80 (`PROJECT.md` notes "Port 8888 for nginx — AdGuard Home occupies port 80"). HTTP-01 challenge requires port 80. DNS-01 challenge requires certbot `dns-cloudflare` plugin + API token configuration + renewal cron. The Cloudflare Tunnel approach is already working (transcription service) and handles SSL at the edge with zero local configuration.

**Do this instead:** Add the brand site as a second hostname in the existing (or new) Cloudflare Tunnel config. SSL is managed by Cloudflare automatically.

### Anti-Pattern 4: Attachment Path URLs in Email Without Considering Semantics

**What people do:** Accept user-provided `path` URLs in attachment objects and pass them directly to Resend — letting Resend's servers fetch arbitrary URLs.

**Why it might be risky:** The email API currently has no outbound URL fetching from user-provided input (intentionally). Adding `path` support delegates URL fetching to Resend's servers, which is fine but changes the security model slightly. Resend will fetch whatever URL is provided.

**Do this instead:** Accept both `path` and `content` (base64) in the API schema but document clearly that `path` causes Resend to fetch the URL. This is acceptable — Resend's servers are responsible for fetching, not ours. Alternatively, only accept `content` (base64) to keep the email service's outbound network behavior unchanged. The simpler approach for v2.0 is supporting both and documenting the distinction.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (personal + small public traffic) | All changes appropriate. Crawl max_pages=30 cap prevents Railway abuse. |
| Growing public traffic | Crawl is the riskiest — each crawl call consumes N * scrape compute time. Add per-wallet crawl rate limiting (same pattern as email `check_and_increment_wallet_limit`) before public launch. |
| High traffic | Cloudflare Tunnel for brand site: Cloudflare CDN caches static assets automatically (Astro static output is cacheable). No changes needed to serve higher traffic. Railway services auto-scale within Hobby tier limits. |

### Scaling Priorities

1. **First bottleneck for crawl:** Railway 30-second request timeout. With max_pages=30 at ~2s/page, worst case is 60s — exceeds Railway's default. Either (a) cap max_pages at 15 to stay under 30s, or (b) implement async job pattern (crawl returns a job_id, poll for results). For v2.0, cap at 15 pages and document. Async jobs are a future milestone feature.

2. **First bottleneck for site traffic:** None for static Astro site. Cloudflare caches static assets at edge. Home server nginx only serves cache misses.

---

## Sources

- `x402-scraping-api/main.py` (live): `scrape_page()`, `extract_content()`, `ScrapeRequest` model, SSRF middleware, `@pay("$0.02")` pattern
- `x402-email-api/main.py` (live): `EmailRequest`, `build_send_params()`, `_do_send()`, `check_and_increment_wallet_limit()` patterns
- `x402-conversion-api/main.py` (live): discriminated union pattern, `sync_html_to_pdf()`, `safe_url_fetcher`, `run_in_threadpool` usage
- `x402-conversion-api/Dockerfile` (live): WeasyPrint system deps, smoke test pattern
- `src/index.ts` (live): APIS dict, apiPost helper, Zod validation patterns for all 11 tools
- `site/astro.config.mjs` (live): `SITE_URL` env var pattern, sidebar structure
- Resend API reference (https://resend.com/docs/api-reference/emails/send-email): cc, bcc, attachments param format confirmed — content (bytes/base64), path (URL), filename, content_type
- mammoth PyPI (https://pypi.org/project/mammoth/): pure Python, DOCX→HTML, limitation on complex layouts
- Cloudflare Tunnel docs: CNAME auto-creation, multiple public hostnames per tunnel, automatic SSL at edge
- `.planning/PROJECT.md`: home server constraints (port 8888, AdGuard Home on port 80, macOS Monterey, existing Cloudflare Tunnel for transcription)

---
*Architecture research for: x402 API Network v2.0 — Site Launch & Platform Polish*
*Researched: 2026-03-15*
