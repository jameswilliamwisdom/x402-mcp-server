# Feature Research

**Domain:** Developer API platform — v2.0 Site Launch & Platform Polish
**Researched:** 2026-03-15
**Confidence:** HIGH (Resend docs confirmed, Firecrawl API pattern confirmed, Cloudflare Tunnel confirmed, API docs conventions well-established), MEDIUM (DOCX conversion tool selection)

---

## Context: v2.0 Scope

v1.1 shipped 11 MCP tools across 8 APIs. v2.0 is about making the platform feel complete and production-grade:

1. **API docs** — 5 new reference pages for v1.1 APIs (scraping, conversion, search, email, transcription)
2. **Custom domain + SSL** — move brand site from `http://10.0.0.2:8888` to a public HTTPS domain
3. **Full site crawl** — multi-page scraping (currently single-page only)
4. **Email attachments + CC/BCC** — richer email sending
5. **DOCX→PDF conversion** — lightweight alternative to LibreOffice

---

## Feature 1: API Documentation Pages (5 new pages)

### What Good API Docs Look Like

The standard for developer API docs is well-established. Stripe, Resend, Tavily, and Firecrawl all follow similar conventions. Missing any of these makes the docs feel incomplete.

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One doc page per API endpoint | Devs navigate to "API Reference" first; a missing page for a shipped API implies it doesn't exist | LOW | 5 new Starlight MDX pages in `/src/content/docs/reference/` |
| Parameter table with name, type, required, default, description | Devs scan parameter tables before reading prose; missing tables = high abandonment | LOW | Markdown table per endpoint, consistent column order |
| Request/response examples (curl + TypeScript) | Devs copy-paste to test; no examples = won't try | LOW | Show both: curl for direct API, MCP tool call for agent use |
| HTTP error codes documented | Agents building on the API need to handle 402, 422, 500 explicitly | MEDIUM | x402's 402 Payment Required is non-standard; document its shape |
| Free test endpoint URL per page | x402 pattern: try without USDC first; undocumented test endpoints create confusion | LOW | Each page shows test endpoint URL prominently, above the paid endpoint |
| Authentication section | Developers need to know how payment works before they can call the API | LOW | Shared "How x402 works" callout component that appears on all reference pages |
| Consistent page structure across all 5 pages | Docs that look different per API feel unmaintained | LOW | Starlight MDX template: Overview → Parameters → Examples → Errors → Free test endpoint |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| MCP tool call example alongside curl | The primary audience is agent developers; showing MCP tool syntax is more useful than curl for them | LOW | Show both in a tabbed code block or sequential examples |
| "What this returns" prose above response schema | Tables alone don't explain how to use the response; a sentence like "The `markdown` field is ready to inject into an LLM context" is high value | LOW | One paragraph per key response field |
| Callout: "No API key required — pay per call with USDC" | Differentiates from every competitor; worth surfacing on every reference page | LOW | Starlight `<Aside type="tip">` component |
| Getting Started narrative guide (separate from reference) | Devs new to x402 need a walkthrough, not just a reference page | LOW | One guide page: install → set wallet → first paid call → check balance |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Interactive API playground (Try It) | Stripe/Twilio have it; devs expect it | High build cost: needs wallet integration in browser, CORS handling, auth flow in docs — not worth it for v2 | Provide copy-paste curl examples and free test endpoint URLs |
| Auto-generated OpenAPI UI (Swagger/Redoc) | "Just use OpenAPI" sounds easy | OpenAPI UI is generic and ugly; doesn't communicate x402 payment flow at all | Hand-write the 5 pages; they're simple enough |
| Video tutorials embedded in docs | "Videos help" | High production cost, go stale quickly, not searchable | Written examples with copy-paste code are better for API docs |

### Feature Dependencies

```
[5 API reference pages]
    └──requires──> [Custom domain + SSL] (docs must be publicly accessible to be useful)
    └──built with──> [Starlight MDX] (already in use for existing docs)
    └──reuses──> [Free test endpoint pattern] (already established for v1.0 APIs)
```

### Edge Cases

- **Free test endpoint for crawl** — crawl is async; the test endpoint should return a fixture (pre-crawled result set) rather than actually crawling, to avoid slow test responses
- **DOCX conversion on docs page** — must note font substitution limitation prominently before showing examples
- **Email docs** — must clarify that `from` address requires a domain verified in Resend (not the caller's arbitrary address)
- **Consistent "Price" callout** — each page should show the per-request USDC cost; currently listed on pricing page but not on reference pages

---

## Feature 2: Custom Domain + SSL

### How It Works

The brand site runs on nginx at `10.0.0.2:8888` (home server). Cloudflare Tunnel already handles the transcription service at `transcribe.jameswisdom.ink`. The same Cloudflare account can expose the brand site on a custom domain with SSL via the same mechanism.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| HTTPS on a public domain | Every production site is HTTPS; HTTP triggers browser security warnings and breaks some agent HTTP clients | LOW | Cloudflare Tunnel terminates TLS at edge; internal traffic to nginx is HTTP — this is fine and standard |
| Custom domain (not Railway subdomain) | Brand credibility; `x402network.com` vs `x402-brand-site-production.up.railway.app` | LOW | Domain purchase + Cloudflare DNS CNAME pointing to tunnel hostname |
| SSL auto-renews | Expired SSL = site goes down; manual renewal is ops overhead | LOW | Cloudflare manages cert renewal; no action required after setup |
| Accessible from public internet | Brand site currently unreachable outside home network | LOW | Cloudflare Tunnel removes need to expose home IP or configure router port forwarding |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cloudflare proxy (DDoS protection, CDN) | Site gets Cloudflare's CDN caching and DDoS protection for free when using their DNS | LOW | Automatic when domain is on Cloudflare — no extra config |
| Static asset caching at Cloudflare edge | Astro/Starlight is a static site; Cloudflare caches HTML/JS/CSS at edge for fast global load | LOW | Set Cache-Control headers in nginx; Cloudflare respects them |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Moving brand site to Railway | "Put everything on Railway for consistency" | Railway adds monthly cost, removes control over the home server deployment that's already working | Keep on home server; Cloudflare Tunnel is the public exposure layer |
| Let's Encrypt direct on home server | "I want my own cert, not Cloudflare's" | Requires exposing port 80/443 to internet for ACME challenge; conflicts with AdGuard Home on port 80; more maintenance | Cloudflare Tunnel's automatic SSL is simpler and sufficient |

### Feature Dependencies

```
[Custom Domain + SSL]
    └──requires──> [Cloudflare account] (already exists — transcription uses it)
    └──requires──> [Domain name registration] (if not already owned)
    └──enables──> [Publicly accessible brand site]
    └──enables──> [All 5 API doc pages being reachable]
```

### Edge Cases

- **Port 8888 conflict with AdGuard Home on port 80** — existing workaround (nginx on 8888) stays in place; Cloudflare Tunnel connects to `localhost:8888` internally, which is fine
- **DNS propagation delay** — new CNAME records can take up to 24h; test with `dig` before announcing the domain
- **Cloudflare SSL mode** — set to "Full" (not "Full Strict" since nginx uses HTTP internally); "Flexible" would also work but is less secure

---

## Feature 3: Full Site Crawl

### What Users Expect from a Crawl API

The standard is set by Firecrawl, Jina Reader, and Cloudflare Browser Rendering (launched March 2026). Users expect crawl APIs to feel like "give me this whole site as clean content."

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `start_url` + crawl all linked pages | Core contract of a crawl API | HIGH | Must follow `<a href>` links, deduplicate, and return results for each page |
| `max_depth` parameter | Control how many link levels deep to traverse (default: 2) | MEDIUM | Depth 0 = start URL only; depth 1 = start URL + directly linked pages; depth 2 = 2 hops |
| `max_pages` limit | Prevent runaway jobs on large sites (hard cap: 50 pages for v2) | LOW | Return partial results + `truncated: true` flag when limit is hit |
| Async job pattern (POST → job_id, GET status) | Crawling 20 pages takes 30-120 seconds — synchronous HTTP will timeout on Railway (60s default) | HIGH | POST /crawl returns `{"job_id": "abc123"}`, GET /crawl/{job_id} returns status + results |
| Per-page output: same schema as single scrape | Each crawled page returns the same fields as the existing single-page scrape endpoint | LOW | Reuse trafilatura + Playwright extraction logic per page |
| Deduplicated URL tracking | Don't visit the same URL twice; prevent redirect loops | MEDIUM | In-memory set of visited URLs per job |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `include_paths` / `exclude_paths` URL filter arrays | Agents often need `/blog/*` only, or want to avoid `/login` and `/checkout`; regex path filtering is a power feature | MEDIUM | Match patterns against URL path only; document as glob-style (`/blog/*`) not full regex |
| robots.txt respect (default: on) | Ethical default; reduces chance of getting IP-blocked | LOW | Parse robots.txt at crawl start, filter disallowed URLs; add `ignore_robots_txt` opt-in escape hatch |
| Sitemap discovery (default: on) | Use XML sitemap as a crawl seed for faster, more complete coverage | MEDIUM | Fetch `/sitemap.xml`, `/sitemap_index.xml`; add discovered URLs to crawl queue |
| Output as clean markdown per page | Agent-ready format; avoids per-page HTML parsing in the agent | LOW | Already doing this in single-page scrape; extend to crawl results |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time crawl progress streaming (SSE/WebSocket) | Users want to see pages coming in live | Breaks stateless API model; requires persistent connections; complicates Railway deployment | Polling pattern: GET /crawl/{job_id} returns progress + partial results |
| Unlimited depth or unlimited page count | "Crawl the whole internet archive-style" | Runaway jobs exhaust Railway memory; potential infinite loops on sites with dynamic URL generation | Hard cap: depth max 5, pages max 100 for v2. Clear error message when hit. |
| JavaScript-heavy SPA crawl (follow JS navigation) | Some SPAs use client-side routing | Playwright already renders JS — regular `<a href>` links work; `pushState`-only navigation requires complex interception | Document limitation: crawl follows `<a href>` links only; JS-only navigation not tracked |
| Cross-domain following | "Crawl all external links too" | Turns a site crawl into a web crawl; scope and cost are unbounded | Stay within the start URL's domain by default; add `allow_external_domains` as opt-in flag later |

### Feature Dependencies

```
[Full Site Crawl]
    └──depends on──> [Single-page scrape] (existing — reuse Playwright + trafilatura per page)
    └──requires──> [Async job infrastructure] (new — job_id storage, status polling endpoint)
    └──independent of──> [Email, DOCX conversion, custom domain]
```

### Edge Cases

- **Redirect loops** — must track all visited URLs (pre-redirect and post-redirect) to prevent infinite loops
- **Non-HTML pages at linked URLs** — PDFs, images, file downloads should be skipped; log them as `skipped` in results
- **Very large pages within crawl** — apply same 50KB markdown truncation as single-page scrape; flag with `truncated: true` per page
- **Crawl timeout** — Railway has a 60s timeout; async job pattern is mandatory; job must complete independently of the HTTP connection
- **Relative vs absolute URL normalization** — `../page`, `//example.com/page`, `/page` must all be resolved to absolute URLs before deduplication
- **Canonical URL conflicts** — some pages have `<link rel="canonical">` pointing elsewhere; respect canonical or crawl the canonical URL
- **Rate limiting by target site** — add configurable delay between page fetches (default: 500ms); back off on 429 responses

### Pricing Note

Crawl is a multi-page operation. Price model options:
1. **Per crawl job** (flat rate, e.g., $0.10) — simple but doesn't scale with page count
2. **Per page crawled** (e.g., $0.02/page — same as single scrape) — scales proportionally but unpredictable total cost

Recommended: per-page pricing (`$0.02 * pages_crawled`), but x402 payment must be pre-authorized or structured as a per-request charge per page. This needs careful design — x402's per-request model is designed for single calls, not multi-page jobs. Consider charging on job submission with a page count estimate, or separate micro-charges per result page.

---

## Feature 4: Email Attachments + CC/BCC

### What Users Expect from Email Attachments

Standard email API behavior (Resend, SendGrid, Postmark). Users assume any email API supports attachments and multiple recipient types.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| File attachments (base64 encoded) | Any real transactional email need (invoices, receipts, reports) requires attachments | MEDIUM | Resend accepts `attachments: [{filename, content (base64)}]`; max 40MB total post-encoding |
| CC recipients (array of strings) | Standard email field; CC is expected in any email API | LOW | Resend supports `cc` as array of strings; pass through directly |
| BCC recipients (array of strings) | Standard email field; BCC is expected in any email API | LOW | Resend supports `bcc` as array of strings; pass through directly |
| Attachment filename in response | Callers need to confirm what was sent | LOW | Echo back the filename list in the response |
| File type documentation (allowed / blocked) | Devs need to know what's safe to send before building | LOW | Allow: PDF, DOCX, XLSX, PNG, JPEG, GIF, TXT, CSV. Block: .exe, .cmd, .bat, .sh, .js, .vbs |
| Clear size limit error | 40MB is post-encoding; a 29MB file encodes to ~40MB — confusing without explanation | LOW | Return 422 with message: "Total attachment size after base64 encoding must not exceed 40MB (original file ~29MB)" |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Inline image support (Content-ID / cid: attachments) | HTML emails with embedded logos/banners that aren't hotlinked — needed for branded transactional email | MEDIUM | Resend supports `content_id` on attachments; cid references in HTML body — document separately from regular attachments |
| Multiple attachments in one call | Obvious utility for "attach invoice + receipt" use case | LOW | Resend accepts array; just pass through with total size validation |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Virus scanning attachments | "API-grade safety" | Adds latency, complex dependency (ClamAV), infrastructure cost; out of scope for micropayment positioning | Block dangerous extensions by MIME type; document this as the security model |
| File URL attachments ("attach this URL") | "I have the file at a URL, not base64" | Requires server-side file download, storage, MIME detection — adds latency and complexity | Caller downloads and base64-encodes before calling; document this in examples |
| Batch email with attachments | "Send the same attachment to 100 people" | Resend explicitly does not support attachments in batch sends (their API limitation) | Single send per call; caller loops — each send is one micropayment |

### Feature Dependencies

```
[Email attachments + CC/BCC]
    └──depends on──> [Resend email API] (existing — additive fields on current endpoint)
    └──no new Railway services required]
    └──ship together with CC/BCC] (same Resend payload update)
```

### Edge Cases

- **Base64 bloat calculation** — 40MB is Resend's post-encoding limit; a 29MB file encodes to ~40MB (base64 adds ~37%); document this math in the API reference
- **MIME type mismatch** — filename extension says `.pdf` but content is a JPEG; validate content type from file magic bytes or trust the filename (caller's responsibility — document this)
- **Multiple attachments total size** — limit applies across all attachments combined, not per file; check sum before sending
- **Inline images in HTML body** — `<img src="cid:logo">` reference must match the `content_id` field on the attachment exactly; document the cid: pattern clearly
- **Empty attachment array** — treat same as no attachments; don't send empty array to Resend
- **Very large base64 string in MCP tool call** — MCP tool calls have payload limits; large attachments (>5MB) may hit tool call size limits; document this and suggest URL-based delivery for large files

---

## Feature 5: DOCX → PDF Conversion

### What Users Expect from DOCX Conversion

Users expect the output PDF to look like the Word document. The reality is more nuanced: formatting fidelity depends heavily on font availability and document complexity.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| DOCX URL → PDF base64 output | Core contract; same interface as existing conversion endpoint | MEDIUM | Add `docx` as a new input_format to existing conversion API |
| Preserve paragraph formatting (bold, italic, headings) | Basic formatting is expected to survive conversion | LOW | LibreOffice headless handles this well |
| Preserve tables | Tables are the most common structured element in Word docs | LOW | LibreOffice handles tables well |
| Preserve images | Images embedded in DOCX should appear in PDF | LOW | LibreOffice handles embedded images |
| File size limit (20MB) with clear error | Large DOCX files cause memory spikes in LibreOffice | LOW | Validate before download; return 422 with size limit message |
| Clear font substitution warning in docs | Missing fonts produce silent visual degradation — users need to know | LOW | Document prominently: "DOCX files using custom fonts not installed on the conversion server will have fonts substituted" |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| No subscription required (per-call micropayment) | Every competitor charges subscription; x402 per-call model is unique | LOW | Already the x402 model — just needs to be communicated in the docs |
| Same unified conversion endpoint as other formats | No new API to learn; just add `input_format: "docx"` to existing conversion call | LOW | Extend existing `/convert` endpoint parameters |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Pixel-perfect font fidelity | "My brand fonts must appear exactly" | Impossible without the original font stack installed on server; LibreOffice substitutes missing fonts silently | Document limitation upfront; suggest embedding fonts in DOCX before sending |
| Complex layout preservation (text boxes, WordArt, floating images) | "My complex newsletter template must convert" | Text boxes and floating layout elements are where LibreOffice degrades most | Document: "Best for text-heavy documents. Complex layouts (text boxes, floating images) may shift." |
| DOCX → editable format (DOCX → DOCX "normalize") | "Clean up my Word doc" | Not a conversion need; out of scope | Not supported |
| Password-protected DOCX | "Convert my secure document" | LibreOffice headless fails silently or with opaque error on password-protected files | Detect and return clear 422: "Password-protected DOCX files are not supported" |
| Batch DOCX conversion | "Convert 50 files" | Same timeout/pricing model constraints as other batch anti-features | Caller loops; each file is one API call |

### DOCX→PDF Library Decision

**Recommended: LibreOffice headless via `python-docx2pdf` wrapper or direct `soffice --headless`**

- LibreOffice is already mentioned in PROJECT.md as the v1.1 approach (now confirmed for v2.0)
- `unoserver` is the modern replacement for the deprecated `unoconv`; better Python 3 compatibility, faster, more reliable
- Quality is better than Pandoc+wkhtmltopdf for documents with tables, images, and complex formatting
- **Main risk:** Railway Docker image size (+300-500MB for LibreOffice); Railway service startup time may increase

**Alternative: Pandoc + wkhtmltopdf**
- Better for text-heavy documents; worse for tables and images
- No LibreOffice dependency — smaller Docker image
- wkhtmltopdf is using an old QtWebKit; modern CSS rendering is poor

**Alternative: Commercial API (ConvertAPI, CloudConvert)**
- Eliminates Docker complexity
- Adds per-conversion cost on top of x402 payment
- External dependency for core feature — avoid

**Decision:** LibreOffice headless (via `unoserver` or direct `soffice --headless --convert-to pdf`) in the Railway Docker image. Accept the image size increase. Ship in isolation if needed by deploying DOCX conversion as a separate Railway service (not alongside HTML→PDF/image conversion which doesn't need LibreOffice).

### Feature Dependencies

```
[DOCX → PDF]
    └──depends on──> [Conversion API] (existing FastAPI service on Railway)
    └──requires──> [LibreOffice headless in Railway Dockerfile] (new system dependency)
    └──optionally──> [Separate Railway service] to isolate LibreOffice image size from other conversion types
    └──independent of──> [Crawl, email attachments, custom domain]
```

### Edge Cases

- **Missing fonts** — LibreOffice substitutes silently; output looks wrong but no error is raised. No fix available server-side. Document clearly.
- **Macros in DOCX** — LibreOffice ignores macros during headless conversion; output is fine for the document content
- **Password-protected DOCX** — LibreOffice will fail or produce empty PDF; detect with `python-docx` before passing to LibreOffice: if `doc.settings.element.find(...)` shows document protection, return 422
- **Very large DOCX** (>10MB) — LibreOffice conversion can take 30-60s for complex 100+ page documents; set a 90s timeout on the conversion subprocess
- **DOCX with external linked images** — images linked from external URLs (not embedded) won't appear in the PDF; document this
- **Corrupted DOCX** — `python-docx` will throw `BadZipFile`; catch and return 422

---

## Cross-Feature Dependencies

```
[Custom Domain + SSL]
    └──required by──> [All 5 API doc pages] (docs must be publicly accessible)
    └──enables──> [Public brand site]

[Full Site Crawl]
    └──depends on──> [Single-page scrape] (existing — reuse per-page extraction)
    └──requires──> [Async job pattern] (new infrastructure)

[Email Attachments + CC/BCC]
    └──depends on──> [Resend email API] (existing endpoint, additive params)

[DOCX → PDF]
    └──depends on──> [Conversion API] (existing FastAPI service)
    └──requires──> [LibreOffice in Docker] (new system dependency, biggest risk)

[API Docs (5 pages)]
    └──depends on──> [Custom Domain] (for public accessibility)
    └──depends on──> [All v1.1 features being fully shipped] (docs for crawl need crawl to exist)
```

---

## MVP Definition

### Launch With (v2.0)

- [x] Custom domain + SSL — gates everything else; do this first
- [x] API docs for all 5 v1.1 APIs — site feels incomplete without them; low complexity, high value
- [x] Email CC/BCC — additive to existing endpoint; ship with attachments in same deploy
- [x] Email attachments (base64, common MIME types) — table stakes for email API completeness
- [x] DOCX→PDF conversion — completes the conversion API story; medium complexity but isolated
- [x] Full site crawl (depth + page limit + async pattern) — table stakes for "scraping API" positioning; highest complexity

### Add After Validation (v2.x)

- [ ] Inline images (cid: attachments) in email — add when users request branded email
- [ ] Crawl URL include/exclude path patterns — add once basic crawl is validated
- [ ] Getting Started narrative guide — add when npm downloads show new-user traffic
- [ ] Crawl with sitemap discovery — add when users complain about missed pages

### Future Consideration (v3+)

- [ ] Interactive API playground — high build cost; defer until traffic justifies it
- [ ] Crawl job webhooks — add when enterprise-style integrations emerge
- [ ] Additional conversion formats (XLSX, PPTX) — add based on user requests

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Custom domain + SSL | HIGH | LOW | P1 — gates public launch |
| API docs for v1.1 APIs (5 pages) | HIGH | LOW | P1 — mandatory for v2 framing |
| Email CC/BCC | HIGH | LOW | P1 — ship with attachments |
| Email attachments | HIGH | MEDIUM | P1 — table stakes |
| DOCX→PDF conversion | MEDIUM | MEDIUM | P1 — completes conversion story |
| Full site crawl (async) | HIGH | HIGH | P1 — table stakes for scraping API |
| Crawl URL path filtering | MEDIUM | LOW (once crawl exists) | P2 |
| Crawl sitemap discovery | MEDIUM | MEDIUM | P2 |
| Inline images in email | LOW | MEDIUM | P2 |
| Getting Started narrative guide | MEDIUM | LOW | P2 |
| Interactive API playground | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.0
- P2: Add when possible, not blocking launch
- P3: Future consideration

---

## Competitor Feature Analysis

### API Documentation

| Feature | Resend Docs | Firecrawl Docs | Stripe Docs | Our Approach |
|---------|-------------|----------------|-------------|--------------|
| Per-endpoint reference page | Yes | Yes | Yes | Yes — 5 new pages |
| Parameter table | Yes | Yes | Yes | Yes |
| curl + SDK examples | Both | Both | Both | curl + MCP tool call |
| Interactive playground | No | No | Yes | No (v2); curl examples |
| Error code reference | Yes | Yes | Yes | Yes — including x402 specific |
| Free tier / test endpoint | Yes | Yes | Yes | Yes — x402 free test pattern |

### Crawl API

| Feature | Firecrawl | Cloudflare Browser Rendering | Our Approach |
|---------|-----------|------------------------------|--------------|
| Depth control | `maxDepth` | `max_discovery_depth` | `max_depth` (1-5) |
| URL filtering | `includePaths`/`excludePaths` (regex) | URL pattern matching | `include_paths`/`exclude_paths` (glob) |
| Page limit | Up to 10,000 | Up to 100,000 | Max 100 (v2) |
| Output format | markdown, HTML, JSON, screenshot | HTML, markdown, JSON, PDF | markdown (default) |
| Async pattern | POST → crawl_id, GET status | POST → crawl_id, GET status | Same pattern |
| robots.txt | Configurable | Respects | Respect by default |
| Pricing | Subscription tiers | Cloudflare Workers pricing | Per-page USDC micropayment — unique |

### Email API

| Feature | Resend | SendGrid | Our Approach |
|---------|--------|----------|--------------|
| Attachments | Base64, 40MB limit | Base64, 30MB limit | Base64, document 29MB practical limit |
| CC/BCC | Array of strings | Supported | Array of strings, pass through |
| Inline images | `content_id` field | Supported | `content_id` — document separately |
| Batch with attachments | Not supported | Supported | Not supported (x402 model) |

---

## Sources

- Firecrawl crawl endpoint docs: https://docs.firecrawl.dev/api-reference/endpoint/crawl-post
- Firecrawl crawl guide: https://www.firecrawl.dev/blog/mastering-the-crawl-endpoint-in-firecrawl
- Cloudflare Browser Rendering /crawl API (March 2026): https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/
- Resend send email API (attachments + CC/BCC confirmed): https://resend.com/docs/api-reference/emails/send-email
- API documentation best practices (Fern, Feb 2026): https://buildwithfern.com/post/api-documentation-best-practices-guide
- API documentation examples (APIdog, 2026): https://apidog.com/blog/api-documentation-example/
- Cloudflare Tunnel + nginx self-hosted site: https://fullmetalbrackets.com/blog/self-host-website-cloudflare-tunnel/
- DOCX to PDF Python comparison: https://michalzalecki.com/converting-docx-to-pdf-using-python/
- unoserver (modern unoconv replacement): https://transloadit.com/devtips/unoconv-for-document-conversion-ease/
- Email attachment size limits guide: https://testmail.app/blog/email-size-limit-guide/
- Azure Communication Services MIME types: https://learn.microsoft.com/en-us/azure/communication-services/concepts/email/email-attachment-allowed-mime-types

---
*Feature research for: x402 API Network v2.0 — Site Launch & Platform Polish*
*Researched: 2026-03-15*
