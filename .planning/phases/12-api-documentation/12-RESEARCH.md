# Phase 12: API Documentation - Research

**Researched:** 2026-03-16
**Domain:** Starlight MDX documentation authoring for x402 API network (5 v1.1 APIs)
**Confidence:** HIGH — all 3 dimensions sourced directly from production codebases and deployed backends
**Method:** MECE decomposition (3 dimensions: INTEGRATION, UX, PITFALLS)

---

## Summary

Phase 12 writes 5 individual Starlight MDX reference pages covering the v1.1 Bismuth APIs: Web Scraping, File Conversion, Web Search, Email Sending, and Audio Transcription. Each page requires a parameter table, curl example (free test + paid), MCP tool call example with natural language prompt, response description, and error code table. The free test endpoint must appear above the paid endpoint on every page (BRAND-04).

The backend schemas, error codes, endpoint paths, and pricing have been fully extracted from production Python source files and the live MCP server TypeScript implementation. All 5 APIs follow a consistent pattern: a free `GET /[op]/test` fixture endpoint (rate-limited at 100/hour per IP) and a paid `POST /[op]` endpoint behind x402 USDC micropayment on Base. The deployed base URLs are confirmed and must be used verbatim in curl examples.

A confirmed pricing discrepancy exists in the existing `api-reference.mdx`: File Conversion, Web Search, and Email prices are wrong. The correct prices from the backend `@pay()` decorators are $0.02, $0.01, and $0.01 respectively. The new pages must use correct prices, and the existing pricing table in `api-reference.mdx` must be corrected in the same work. The MDX files must use JSX comment syntax (`{/* */}`) not HTML comment syntax — the HTML syntax causes confirmed build failures in this codebase.

**Primary recommendation:** Use one MDX file per API under `site/src/content/docs/apis/`, following the parameter table + curl + MCP tool call + error code template. Register all 5 slugs manually in `astro.config.mjs`. Correct pricing drift in the same commit. Extend deploy.sh smoke tests to cover the 5 new URLs.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | API reference page for Web Scraping API with parameter table, curl + MCP tool call examples, error codes | Full schema extracted from `x402-scraping-api/main.py` and `src/index.ts`; page template confirmed from UX dimension; all error codes catalogued (INTEGRATION) |
| DOCS-02 | API reference page for File Conversion API with parameter table, curl + MCP tool call examples, error codes | Discriminated union schema (`image`/`csv`/`html_pdf`) fully documented from `x402-conversion-api/main.py`; type-conditional parameter table pattern confirmed (UX + PITFALLS) |
| DOCS-03 | API reference page for Web Search API with parameter table, curl + MCP tool call examples, error codes | Full Tavily-backed schema from `x402-search-api/main.py`; per-wallet daily limit (50/day) documented; price confirmed $0.01 correcting existing doc error (INTEGRATION + PITFALLS) |
| DOCS-04 | API reference page for Email Sending API with parameter table, curl + MCP tool call examples, error codes | Full Resend-backed schema from `x402-email-api/main.py`; fixed From address and dual rate limits (wallet + domain) documented (INTEGRATION + PITFALLS) |
| DOCS-05 | API reference page for Audio Transcription API with parameter table, curl + MCP tool call examples, error codes | Full schema from `x402-transcription-api/main.py` + `config.py`; branching response schema (`segments` vs `timestamps`) documented; billing-on-download note included (INTEGRATION + PITFALLS) |

---

## Standard Stack

### Starlight / Astro Versions

| Component | Version | File |
|-----------|---------|------|
| `@astrojs/starlight` | `^0.37.7` | `site/astro.config.mjs` |
| Astro | `^5.18.0` | `site/astro.config.mjs` |

### MCP Server Context

| Component | Value | Source |
|-----------|-------|--------|
| MCP package | `x402-mcp-server@1.1.0` | `src/index.ts` line 188 |
| Payment env var | `X402_PRIVATE_KEY` | `src/index.ts` line 85 |
| Payment SDK | `x402-fetch` | `src/index.ts` line 16 |
| Chain | Base (L2 Ethereum) | `src/index.ts` line 19 |
| Token | USDC (6 decimals) | `src/index.ts` line 110 |

### Starlight Components Available

All from `import { ... } from '@astrojs/starlight/components'`:

| Component | Purpose | Used By |
|-----------|---------|---------|
| `Aside` | Callout boxes (tip/note/caution/danger) | All reference pages — the "No API key" tip |
| `Tabs` / `TabItem` | Tabbed content groups | Optional for conversion API type variants |
| `Code` | Syntax-highlighted code from variables | Not needed — use fenced code blocks |
| `Steps` | Numbered step lists | Not needed for reference pages |
| `Card` / `CardGrid` | Feature cards | Not needed for reference pages |
| `Badge` | Inline status labels | Not needed for reference pages |

**Rule:** Import only `Aside` on the new reference pages. The existing `api-reference.mdx` imports only `Aside` — follow that minimal pattern.

### Pricing (Verified from Backend Source — Authoritative)

| API | MCP Tool | Free Test Endpoint | Paid Endpoint | Price |
|-----|----------|--------------------|---------------|-------|
| Web Scraping | `x402_scrape_url` | `GET /scrape/test` | `POST /scrape` | $0.02 USDC |
| File Conversion | `x402_convert_file` | `GET /convert/test` | `POST /convert` | $0.02 USDC |
| Web Search | `x402_web_search` | `GET /search/test` | `POST /search` | $0.01 USDC |
| Email Sending | `x402_send_email` | `GET /send/test` | `POST /send` | $0.01 USDC |
| Audio Transcription | `x402_transcribe_audio` | `GET /transcribe/test` | `POST /transcribe` | $0.05 USDC |

**Sources for prices:** `@pay()` decorators in each backend `main.py` and `config.py`. These override the placeholder table in `api-reference.mdx` lines 218–223 which is incorrect for conversion ($0.05 vs $0.02), web search ($0.02 vs $0.01), and email ($0.02 vs $0.01).

### Deployed Base URLs (Verified)

| API | Base URL |
|-----|----------|
| Web Scraping | `https://x402-scraping-api-production.up.railway.app` |
| File Conversion | `https://x402-conversion-api-production.up.railway.app` |
| Web Search | `https://x402-search-api-production.up.railway.app` |
| Email Sending | `https://x402-email-api-production.up.railway.app` |
| Audio Transcription | `https://transcribe.jameswisdom.ink` |

---

## Architecture Patterns

### File Layout

```
site/src/content/docs/
├── getting-started.mdx          (existing)
├── wallet-setup.mdx             (existing)
├── api-reference.mdx            (existing — update pricing table, keep as overview)
└── apis/
    ├── scraping.mdx             (DOCS-01: x402_scrape_url)
    ├── file-conversion.mdx      (DOCS-02: x402_convert_file)
    ├── web-search.mdx           (DOCS-03: x402_web_search)
    ├── email.mdx                (DOCS-04: x402_send_email)
    └── audio-transcription.mdx  (DOCS-05: x402_transcribe_audio)
```

### Sidebar Config Update (`site/astro.config.mjs`)

Add a new `APIs` group with manual item ordering (preserves DOCS-01 through DOCS-05 order; manual sidebar is already established):

```javascript
sidebar: [
  {
    label: 'Getting Started',
    items: [
      { slug: 'getting-started' },
      { slug: 'wallet-setup' },
    ],
  },
  {
    label: 'Reference',
    items: [
      { slug: 'api-reference' },
    ],
  },
  {
    label: 'APIs',
    items: [
      { slug: 'apis/scraping' },
      { slug: 'apis/file-conversion' },
      { slug: 'apis/web-search' },
      { slug: 'apis/email' },
      { slug: 'apis/audio-transcription' },
    ],
  },
],
```

Slug mirrors file path relative to `src/content/docs/` without extension. `'apis/scraping'` for `src/content/docs/apis/scraping.mdx`.

### Per-Page Frontmatter Pattern

```mdx
---
title: Web Scraping API
description: Scrape any URL and return structured markdown, links, tables, and metadata. $0.02 USDC per call.
sidebar:
  label: Web Scraping
  order: 1
---
```

`sidebar.label` shortens the sidebar text. `sidebar.order` is optional if using manual items (order is already explicit).

### Per-Page Content Template

Every reference page follows this identical section structure:

```mdx
---
title: [API Name] API
description: [One-line description with price]
---

import { Aside } from '@astrojs/starlight/components';

[1-2 sentence description of what the API does.]

## Endpoints

**Free test endpoint:** `GET /[path]/test` — returns fixture data, no wallet required.
**Paid endpoint:** `POST /[path]` — $X.XX USDC on Base per call.

<Aside type="tip" title="No API key required">
Add `X402_PRIVATE_KEY` to your MCP config to enable paid calls — each request automatically
settles $X.XX USDC on Base. Use the free test endpoint to confirm the response schema
before enabling payments.
</Aside>

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `param`   | string | Yes   | —       | Description |

## Example — curl

```bash
# Free test (no wallet required)
curl https://[base-url]/[path]/test

# Paid call (requires x402-fetch or x402-mcp-server — handles X-Payment header automatically)
curl -X POST https://[base-url]/[path] \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

## Example — MCP Tool Call

> "[Natural language prompt the agent would use]"

```json
{
  "tool": "x402_[tool_name]",
  "arguments": {
    "param": "value"
  }
}
```

## Returns

[Description of response shape with example JSON.]

## Error Codes

| Code | Meaning |
|------|---------|
| `402` | Payment required — x402 handshake (handled automatically by MCP server) |
| `422` | [API-specific validation error] |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
```

**Critical constraint (BRAND-04):** Free test endpoint must appear above the paid endpoint in `## Endpoints`. Always free first, paid second.

### Parameter Table Format

Exact column set from `api-reference.mdx`:

```markdown
| Parameter | Type    | Required | Default | Description                                          |
|-----------|---------|----------|---------|------------------------------------------------------|
| `url`     | string  | Yes      | —       | Full URL to scrape (http/https, max 2048 chars)      |
| `wait_for`| string  | No       | —       | CSS selector to wait for before extracting           |
```

Rules:
- Parameter names in backticks
- Type in plain text (string, integer, boolean, string enum)
- Required: `Yes` or `No`
- Default: `—` for required params or optional params with no default
- Defaults for optional params: show actual value (`5`, `false`, `"jpeg"`)

### MCP Tool Call Block Format

Always precede the JSON block with a natural language blockquote:

```mdx
> "Scrape the blog post at https://example.com/article and return the markdown content."

```json
{
  "tool": "x402_scrape_url",
  "arguments": {
    "url": "https://example.com/article"
  }
}
```
```

### Pricing SYNC Comment

Place a JSX comment near each hardcoded price (JSX syntax only — HTML comments break the MDX parser):

```mdx
{/* SYNC: price must match src/index.ts @pay() decorator and PricingTable.astro */}
```

### x402 Auth Pattern Summary (Cross-Cutting)

All 5 APIs use the same x402 payment flow:
1. Client sends request without payment header
2. Server responds HTTP 402 with payment payload
3. `x402-fetch` / MCP server parses the 402, signs USDC transfer on Base, retries with `X-Payment` header
4. Server validates payment and returns actual response

Free test endpoints require no auth — plain HTTP GET, no header. Raw curl against paid endpoints always returns 402 without x402 tooling. The MCP server handles the full handshake transparently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sidebar navigation for new pages | New autogenerate config | Manually add `{ slug: 'apis/...' }` entries to sidebar in `astro.config.mjs` | Manual sidebar already established; mixing autogenerate would require restructuring the entire config |
| Parameter documentation UI | Custom React/Astro component | Standard Markdown table (Parameter, Type, Required, Default, Description) | Pattern already established in `api-reference.mdx`; Starlight's Expressive Code handles code styling automatically |
| "No API key" callout | Custom styled component | `<Aside type="tip" title="No API key required">` | Already used in `api-reference.mdx` for all paid tools |
| Code syntax highlighting | Custom highlight configuration | Starlight's built-in Expressive Code | Zero config; autodetects `json`, `bash` |
| Free test endpoint UI | Special component | Bold text: `**Free test endpoint:** GET /op/test` then `**Paid endpoint:** POST /op` | Pattern established in `api-reference.mdx`; BRAND-04 only requires free URL above paid URL |
| Conversion type variants | Tabs component per type | Single parameter table with "(image only)" notes in Description column | Tabs add complexity; the existing page style uses conditional notes — simpler and consistent |

---

## Common Pitfalls

### P1: HTML Comments Break MDX Parser (CONFIRMED BUG — this codebase)

HTML comment syntax (`<!-- -->`) is not valid JSX. Using it in any `.mdx` file throws "Unexpected character `!`" and fails the build. Always use `{/* comment text */}` in MDX files. The existing `api-reference.mdx` already uses JSX comments — match that.

**Source:** Phase 3 SUMMARY (03-03-SUMMARY.md confirmed bug).

### P2: Pricing Drift Between Three Sources

The new pages will hardcode prices. The same price appears in `src/index.ts`, backend `@pay()` decorators, and `PricingTable.astro`. These sources drift independently. The existing `api-reference.mdx` pricing table already contains wrong prices for three of the five new APIs.

**Correct prices (verified from backend source):**
- Conversion: $0.02 (existing doc says $0.05 — wrong)
- Web Search: $0.01 (existing doc says $0.02 — wrong)
- Email: $0.01 (existing doc says $0.02 — wrong)
- Scraping: $0.02 (correct)
- Transcription: $0.05 (correct)

Place a `{/* SYNC */}` JSX comment near each price. Correct the existing pricing table in `api-reference.mdx` in the same commit as writing the web search page.

**Source:** `@pay()` decorators in all 5 backend `main.py`/`config.py` files + `src/index.ts`.

### P3: Sidebar Slug Mismatch

A slug like `'api/scraping'` in `astro.config.mjs` when the file is at `src/content/docs/apis/scraping.mdx` (missing the plural `apis`) silently omits the page from the sidebar with no build error. Slug must exactly mirror the file path relative to `src/content/docs/` without extension.

**Source:** `site/astro.config.mjs` current configuration.

### P4: Sidebar Entry Not Registered

New MDX files build as pages but do not appear in the sidebar unless explicitly added to the `sidebar` array in `astro.config.mjs`. The site uses a manually-defined sidebar — there is no autogenerate fallback.

**Source:** Phase 3 RESEARCH.md, `site/astro.config.mjs`.

### P5: Free Endpoint Listed After Paid Endpoint

Listing the paid endpoint first violates BRAND-04. The `## Endpoints` section must always have free test on line 1, paid on line 2. The template in Architecture Patterns enforces this.

**Source:** REQUIREMENTS.md BRAND-04.

### P6: Incorrect Prices in Existing Docs

The existing `api-reference.mdx` pricing table (lines 218–223) uses wrong values for conversion ($0.05), web search ($0.02), and email ($0.02). The new per-API pages must use correct prices, and the existing table must also be corrected to avoid contradiction.

**Source:** INTEGRATION dimension; verified against all five backend source files.

### P7: Scrape Success=False is HTTP 200

Timeout, browser errors, Cloudflare blocks, and non-HTML content all return HTTP 200 with `"success": false` in the body. Callers checking only HTTP status will incorrectly treat these as successes. The docs must show the `success: false` response shape and list all `error` field values.

**Source:** `x402-scraping-api/main.py` error handling.

### P8: CSV Conversion Response is Base64-Encoded JSON

The conversion API returns base64-encoded data for all three types including CSV. For `type: "csv"`, the caller must base64-decode `data` to get the JSON array of objects. Docs that skip this step will confuse readers who expect raw JSON.

**Source:** `x402-conversion-api/main.py` response model.

### P9: Transcription Response Schema Branches on `word_timestamps`

The transcription response has `segments` (sentence-level, always present when `word_timestamps=false`) OR `timestamps` (word-level, present when `word_timestamps=true`). These fields are mutually exclusive. Both schema variants must be shown as separate examples.

**Source:** `x402-transcription-api/main.py`.

### P10: Email From Address Not Configurable

All emails are sent from `x402 Email API <noreply@jameswisdom.ink>`. The `reply_to` field allows recipients to reply to the caller's address, but the From address cannot be overridden. Docs must state this clearly.

**Source:** `x402-email-api/main.py` hardcoded `FROM_ADDRESS`.

### P11: Transcription Charges on Duration Limit Violations

Audio files exceeding 10 minutes still incur the $0.05 charge because payment is deducted at download + probe time, before the duration check refusal. x402 has no refund mechanism. This must be documented explicitly.

**Source:** `x402-transcription-api/main.py` billing note.

### P12: Conversion API `type` Discriminator is Non-Obvious

`x402_convert_file` uses a discriminated union. `type: "image"` unlocks `format`, `width`, `height`. `type: "csv"` and `type: "html_pdf"` accept only `url`. The parameter table should note which optional fields apply to which type using the "(image only)" annotation pattern.

**Source:** `x402-conversion-api/main.py` Pydantic models; PITFALLS dimension.

### P13: deploy.sh Smoke Tests Do Not Cover New Page URLs

After deploy, `site/deploy.sh` smoke tests only cover existing pages (/, /pricing/, /getting-started/, /api-reference/, /wallet-setup/). The 5 new API pages will not be smoke-tested. Extend `deploy.sh` with `smoke_check` calls for each new page URL.

**Source:** `site/deploy.sh` current content.

### P14: Broken Internal Links — Use Absolute Paths With Trailing Slashes

Links from nested pages (e.g., `apis/web-scraping.mdx`) back to root pages must use absolute paths with trailing slashes: `[API Overview](/api-reference/)`. The deployment has a known nginx behavior where paths without trailing slashes redirect incorrectly until an nginx reload.

**Source:** Phase 11 STATE.md; `site/deploy.sh` smoke tests.

### P15: Code Fences Inside MDX JSX Components Require Correct Indentation

Fenced code blocks inside `<Tabs>` or `<Steps>` without correct 3-space indentation can cause MDX to mismatch structure. Follow the exact pattern from `getting-started.mdx`. The reference pages do not need Tabs or Steps, so this pitfall is low-risk for Phase 12 — only relevant if Tabs are used for the conversion type variants.

**Source:** `site/src/content/docs/getting-started.mdx`; PITFALLS dimension.

### P16: Parameter Table Showing `—` for Optional Params That Have Defaults

For optional parameters with defined defaults (e.g., `max_results: 5` for web search, `word_timestamps: false` for transcription, `format: "jpeg"` for image conversion), show the actual default value in the Default column rather than `—`.

**Source:** UX dimension; `src/index.ts` Zod schemas.

---

## Code Examples

### Complete API Reference Data

#### 1. Web Scraping API (DOCS-01)

**MCP tool:** `x402_scrape_url` | **Price:** $0.02 USDC | **Base URL:** `https://x402-scraping-api-production.up.railway.app`

Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | — | Page to scrape (http/https, max 2048 chars) |
| `wait_for` | string | No | — | CSS selector to wait for before extraction (for SPAs) |

Free test curl:
```bash
curl https://x402-scraping-api-production.up.railway.app/scrape/test
```

Paid curl:
```bash
curl -X POST https://x402-scraping-api-production.up.railway.app/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

MCP tool call:
```json
{
  "tool": "x402_scrape_url",
  "arguments": {
    "url": "https://example.com",
    "wait_for": ".article-body"
  }
}
```

Error codes: 400 (SSRF), 402 (payment), 422 (validation), 429 (rate limit), 503 (browser unavailable), 200+`success:false` (timeout / browser_error / non_html_content / blocked_by_protection)

#### 2. File Conversion API (DOCS-02)

**MCP tool:** `x402_convert_file` | **Price:** $0.02 USDC | **Base URL:** `https://x402-conversion-api-production.up.railway.app`

Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | — | Conversion type: `"image"`, `"csv"`, or `"html_pdf"` |
| `url` | string | Yes | — | Source file URL (http/https, max 2048 chars, max 10MB) |
| `format` | string | No (image only) | `"jpeg"` | Output format: `"jpeg"`, `"png"`, `"webp"`, `"gif"` |
| `width` | integer | No (image only) | — | Target width in pixels (1–8000) |
| `height` | integer | No (image only) | — | Target height in pixels (1–8000) |

Response: `data` is always base64-encoded. For `type: "csv"`, base64-decode `data` to get a JSON array of objects.

Free test curl:
```bash
curl https://x402-conversion-api-production.up.railway.app/convert/test
```

Error codes: 400 (SSRF), 402 (payment), 422 (validation), 429 (rate limit), 200+`success:false` (download_error / http_error / conversion_error / output_too_large)

#### 3. Web Search API (DOCS-03)

**MCP tool:** `x402_web_search` | **Price:** $0.01 USDC | **Base URL:** `https://x402-search-api-production.up.railway.app`

Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | — | Search query (min 1, max 400 chars) |
| `max_results` | integer | No | `5` | Number of results (1–10) |
| `include_answer` | boolean | No | `false` | Include Tavily-synthesized answer above results |
| `include_domains` | array | No | — | Restrict results to these domains (max 20) |
| `exclude_domains` | array | No | — | Exclude these domains (max 20) |

Rate limit: 50 queries/day per wallet, resets midnight UTC.

Free test curl:
```bash
curl https://x402-search-api-production.up.railway.app/search/test
```

Error codes: 402 (payment), 422 (validation), 429 (daily wallet limit or free test rate limit), 500 (Tavily error), 503 (Tavily credit exhausted)

#### 4. Email Sending API (DOCS-04)

**MCP tool:** `x402_send_email` | **Price:** $0.01 USDC | **Base URL:** `https://x402-email-api-production.up.railway.app`

Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `to` | string | Yes | — | Recipient email address |
| `subject` | string | Yes | — | Email subject (max 998 chars, RFC 5321) |
| `body` | string | Yes | — | Email body — HTML or plain text (max 100 KB); HTML auto-detected |
| `reply_to` | string | No | — | Reply-to address |

Fixed sender: `x402 Email API <noreply@jameswisdom.ink>`. From address cannot be overridden.
Rate limits: 10 emails/day per wallet; 5 emails/day per wallet per recipient domain. Both reset midnight UTC.

Free test curl (no real email sent):
```bash
curl https://x402-email-api-production.up.railway.app/send/test
```

Error codes: 402 (payment), 422 (validation), 429 (wallet limit or domain limit or free test rate limit), 500 (Resend auth error), 503 (Resend quota exhausted or busy)

#### 5. Audio Transcription API (DOCS-05)

**MCP tool:** `x402_transcribe_audio` | **Price:** $0.05 USDC | **Base URL:** `https://transcribe.jameswisdom.ink`

Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | — | Audio file URL (http/https, public, max 25MB, max 10 min) |
| `language` | string | No | — | ISO 639-1 language hint (e.g., `"en"`) — omit for auto-detect |
| `word_timestamps` | boolean | No | `false` | `true` for word-level timing, `false` for segment-level |

Response branches: `word_timestamps=false` returns `segments` array; `word_timestamps=true` returns `timestamps` array. The fields are mutually exclusive.

Hard limits: 25MB file size, 10-minute duration. Payment charged on download — duration limit violations still incur the $0.05 charge.

Free test curl:
```bash
curl https://transcribe.jameswisdom.ink/transcribe/test
```

Error codes: 400 (SSRF), 402 (payment), 413 (file >25MB), 422 (download failed / format unreadable / duration exceeded), 429 (free test rate limit), 500 (model error), 503 (model not loaded)

---

## State of the Art

### Existing Documentation Baseline

The existing `api-reference.mdx` covers MCP tools 1–6 (screenshot, PDF, sentiment, market_overview, intelligence, plus a pricing stub for the 5 new APIs). The stub at lines 218–223 will be replaced/corrected by Phase 12. The existing page establishes all formatting conventions that Phase 12 must follow.

### MDX Authoring in Starlight 0.37.x

Starlight uses Expressive Code for syntax highlighting — zero configuration needed for `bash` and `json` blocks. The `@astrojs/starlight/components` import pattern is stable. Starlight auto-generates the Table of Contents from `##` and `###` headings with no frontmatter override needed for standard reference pages.

### x402 Protocol Context for Docs Readers

The x402 payment flow is a 402/re-request cycle that `x402-fetch` and the MCP server handle automatically. Documentation should emphasize that callers do not manually construct payment headers — the MCP server or `x402-fetch` handles the full handshake. The free test endpoints exist precisely so users can verify response schemas without setting up a wallet.

---

## Open Questions

1. **Exact slug names for the 5 new pages:** DIM-UX recommends `apis/scraping`, `apis/file-conversion`, `apis/web-search`, `apis/email`, `apis/audio-transcription`. DIM-PITFALLS uses `apis/web-scraping`, `apis/email-sending`. These differ slightly. Planner should pick one naming convention and apply it consistently to both file paths and sidebar slugs.

2. **What to do with the existing `api-reference.mdx` pricing table:** Correct it in the same commit as the web search page, or in a dedicated task? Recommendation: correct it in the web search task (DOCS-03) since that is where the known $0.02 → $0.01 discrepancy lives.

3. **deploy.sh smoke test URL paths:** Depend on slug decision above (open question 1). Must be resolved before the deploy task.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on all facts. Slug naming minor variation (DIM-UX: `apis/scraping` vs DIM-PITFALLS: `apis/web-scraping`) noted as open question — not a conflict, just inconsistency in examples. Both dimensions recommend manual sidebar registration. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Optional sections included: Phase Requirements, State of the Art, Open Questions. |
| Dimension Coverage | PASS | INTEGRATION: all 5 API schemas, error codes, auth pattern, and pricing pitfalls integrated. UX: file layout, sidebar config, frontmatter, component usage, parameter table format, and free/paid endpoint block integrated. PITFALLS: all 12 pitfalls (1 MEDIUM confidence, 11 HIGH) integrated. |
| Requirement Coverage | PASS | DOCS-01 through DOCS-05 each map to specific API schema documentation from INTEGRATION dimension, page template from UX dimension, and relevant pitfall guards from PITFALLS dimension. |

---

## Sources

### Primary (HIGH confidence — sourced directly from production code)

- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — MCP tool definitions, Zod schemas, endpoint URLs, pricing, all 5 tool implementations
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — Scraping API routes, Pydantic models, error handling, SSRF protection
- `/Users/jameswisdom/projects/x402-mcp-server/x402-conversion-api/main.py` — Conversion API discriminated union, limits, error codes, all three types
- `/Users/jameswisdom/projects/x402-mcp-server/x402-search-api/main.py` — Tavily integration, per-wallet rate limits, response shaping
- `/Users/jameswisdom/projects/x402-mcp-server/x402-email-api/main.py` — Resend integration, HTML detection, rate limits, fixed From address
- `/Users/jameswisdom/projects/x402-mcp-server/x402-transcription-api/main.py` — Transcription routes, branching response schema, billing note
- `/Users/jameswisdom/projects/x402-mcp-server/x402-transcription-api/config.py` — Model config, price, hard limits
- `/Users/jameswisdom/projects/x402-mcp-server/site/src/content/docs/api-reference.mdx` — Existing doc format, component imports, parameter table format, MCP call examples, pricing stub discrepancy
- `/Users/jameswisdom/projects/x402-mcp-server/site/astro.config.mjs` — Sidebar config, Starlight version, current structure
- `/Users/jameswisdom/projects/x402-mcp-server/site/src/content/docs/getting-started.mdx` — Tabs/Steps/Aside component nesting patterns
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/phases/03-brand-site-build/03-03-SUMMARY.md` — MDX HTML comment bug and PNG scanline bug (confirmed in this codebase)
- `/Users/jameswisdom/projects/x402-mcp-server/site/deploy.sh` — Smoke test coverage gap for new pages
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/STATE.md` — nginx trailing slash issue on production

### Secondary (MEDIUM confidence)

- Starlight official docs `starlight.astro.build/components/asides/` — Aside props confirmed
- Starlight official docs `starlight.astro.build/guides/sidebar/` — slug format for subdirectory pages
- Starlight official docs `starlight.astro.build/reference/frontmatter/` — sidebar.label, sidebar.order fields

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH (sourced directly from production Python backends and live MCP TypeScript)
- UX: HIGH (sourced from codebase + official Starlight docs)
- PITFALLS: HIGH (11 of 12 pitfalls HIGH confidence; 1 pitfall MEDIUM — Aside inside Steps blank line, inferred from parser behavior)

**Research date:** 2026-03-16
**Valid until:** Until any of the 5 backend APIs change their endpoint paths, schemas, or pricing, or until Starlight major version upgrade
**Dimensions researched:** INTEGRATION, UX, PITFALLS
