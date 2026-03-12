# Phase 5: Web Scraping API - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

A new Railway service (`x402-scraping-api`) that accepts a URL and returns structured JSON — markdown-converted page text, extracted links, tables, and page metadata. JS-rendered pages supported via Playwright. A `wait_for` CSS selector param for async SPA content. SSRF protection validates resolved IPs before outbound fetch. Free test endpoint with fixture data.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<specifics>
## Specific Ideas

- Response pattern: `{success: true, url, final_url, markdown, links, tables, images, metadata, warnings}` on success
- Error pattern: `{success: false, error: "error_code", detail: "human-readable message"}` on failure
- Metadata should include: title, description, og:image, og:title, canonical URL, language, status_code, key headers
- Fixture should demonstrate the full response shape so agent developers can see exactly what they'll get

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-web-scraping-api*
*Context gathered: 2026-03-12*
