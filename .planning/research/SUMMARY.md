# Project Research Summary

**Project:** x402 API Network — v2.0 Site Launch & Platform Polish
**Domain:** Developer API platform (MCP server + Python FastAPI microservices + static brand site)
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

The x402 v2.0 milestone is a polish and completeness pass on a working platform — not a greenfield build. The v1.1 stack (TypeScript MCP server, Python/FastAPI microservices on Railway, Astro/Starlight brand site on a home server behind Cloudflare Tunnel) is fully locked in. Research confirms that all five v2.0 features are well-scoped, additive to existing services, and require no new infrastructure except a single Cloudflare Tunnel hostname rule. The recommended build sequence is domain/SSL first (gates the public site), then docs content, then three parallel backend features (DOCX conversion, email attachments, crawl endpoint), then MCP server update, then npm publish.

The only significant design decision resolved by research is the DOCX-to-PDF library choice. The user asked for a lightweight alternative to LibreOffice; research confirms that mammoth + WeasyPrint (a two-step DOCX → HTML → PDF pipeline) satisfies the v2.0 use case with zero new system dependencies and zero Docker image size cost. LibreOffice adds ~300MB to the Railway image and introduces cold-start penalty — it is explicitly deferred to a future milestone for use cases requiring pixel-perfect layout fidelity.

The highest-risk feature is multi-page crawling. The Railway 60-second request timeout makes a synchronous crawl endpoint viable only with a conservative max_pages cap (15 pages recommended for v2.0 synchronous implementation). An async job pattern (POST returns job_id, GET polls status) is the correct architecture for higher page counts and is flagged as a v2.x follow-on. Two security issues must be addressed during crawl implementation: SSRF validation must be applied to every discovered URL (not just the initial user-supplied URL), and all `http://` / `https://` scheme filtering must happen before any URL is queued.

## Key Findings

### Recommended Stack

The v1.1 stack handles all five features without new packages except two: `mammoth>=1.12.0` (pure Python, no system deps) added to `x402-conversion-api/requirements.txt`, and `crawlee[playwright]>=1.5.0` added to `x402-scraping-api/requirements.txt`. The Resend SDK (`resend>=2.0.0,<3.0.0`) already supports CC/BCC/attachments at the current pinned version range. Astro/Starlight are already at current versions with no update needed. The Cloudflare Tunnel infrastructure is already in place — only a config addition is required.

**Core technology decisions:**
- **mammoth + WeasyPrint (not LibreOffice)** — DOCX conversion pipeline: pure Python, zero Docker size cost, zero system deps, production release March 12, 2026. Fidelity is semantic (text, headings, tables, images preserved; complex Word layouts partially lost). Correct choice for content documents.
- **crawlee[playwright] 1.5.0** — Multi-page crawling: built-in same-domain filtering, max_crawl_depth, URL deduplication, no Redis required. Uses the existing Playwright browser install. Verify against pinned `playwright==1.44.0` for compatibility before merging.
- **Cloudflare Tunnel (existing, one new ingress rule)** — Brand site public exposure: add one ingress rule to `~/.cloudflared/config.yml`. SSL is automatic at Cloudflare's edge. No certbot, no nginx SSL config, no port-forwarding.
- **Resend SDK 2.23.0** — Email attachments/CC/BCC: already within `>=2.0.0,<3.0.0` constraint; zero requirements.txt changes needed.

### Expected Features

Research confirms all five v2.0 features are table-stakes for a production-grade developer API platform. The docs, domain, and email features are low-risk; crawl is the only high-complexity item.

**Must have (table stakes):**
- Custom domain + SSL — every production site is HTTPS; site is currently unreachable from the public internet
- API reference pages for all 5 v1.1 APIs — missing docs imply the APIs don't exist; abandonment is high without parameter tables and examples
- Per-endpoint parameter tables, curl + MCP tool call examples, error codes — developer audience expects this pattern (Stripe/Resend/Firecrawl convention)
- Email CC/BCC — standard email API fields, users assume they exist
- Email attachments (base64, common MIME types, 25MB practical limit) — required for any real transactional email use case
- DOCX-to-PDF conversion — completes the conversion API story
- Full site crawl with max_depth + max_pages + per-page extraction — table stakes for "scraping API" positioning

**Should have (competitive differentiators):**
- "No API key — pay per call with USDC" callout on every reference page — unique positioning vs every competitor
- MCP tool call example alongside curl on each docs page — primary audience is agent developers, not curl users
- Free test endpoint URL prominently shown above paid endpoint on each docs page
- Crawl URL include/exclude path filtering (`/blog/*` patterns) — power feature, add once basic crawl ships
- Crawl robots.txt respect (default on) + sitemap discovery — competitive parity with Firecrawl

**Defer to v2.x:**
- Async job pattern for crawl (POST to job_id, GET status) — required for >15 pages; defer until synchronous crawl is validated
- Inline images (cid: attachments) in email — add when users request branded transactional email
- Getting Started narrative guide — add when new-user traffic signals demand
- Interactive API playground — high build cost, defer until traffic justifies it

### Architecture Approach

All five v2.0 features are additive to three existing Railway services and one static site, with no new Railway services required. The crawl feature gets a dedicated `POST /crawl` endpoint (not a parameter on `/scrape`) because it returns a different schema (array of results), carries a different price point ($0.05 vs $0.02), and warrants independent rate limiting. DOCX conversion extends the existing `ConvertRequest` discriminated union with a new `DocxConvertRequest` type — it stays in the conversion service because mammoth is pure Python and WeasyPrint is already installed there. Email additions are purely additive Pydantic model fields.

**Major components and their v2.0 changes:**
1. `x402-scraping-api/main.py` — Add `CrawlRequest` model + `POST /crawl` endpoint + BFS crawl loop reusing existing `scrape_page()` / `extract_content()`; add `fixture_crawl.json` for `GET /crawl/test`
2. `x402-conversion-api/main.py` — Add `DocxConvertRequest` to discriminated union + `sync_docx_to_pdf()` via mammoth-to-WeasyPrint chain; add `mammoth>=1.12.0` to requirements.txt
3. `x402-email-api/main.py` — Add `cc`, `bcc`, `attachments` to `EmailRequest` and `build_send_params()`; no requirements changes
4. `src/index.ts` — Add new `x402_crawl_site` tool (12th tool); update `x402_send_email` and `x402_convert_file` Zod schemas
5. `site/src/content/docs/api-reference.mdx` — Add all 5 v1.1 API docs (currently only 6 tools documented out of 11)
6. `~/.cloudflared/config.yml` — Add ingress rule: `x402.jameswisdom.ink` to `http://localhost:8888`

### Critical Pitfalls

1. **Cloudflare SSL "Flexible" mode causes infinite redirect loop** — Use Tunnel (HTTP backend, set mode to "Full"), or "Full (Strict)" with a Cloudflare Origin Certificate. "Flexible" + any HTTP-to-HTTPS redirect in nginx produces `ERR_TOO_MANY_REDIRECTS`. Verify SSL mode setting before adding any redirect rules to nginx.

2. **Discovered crawl URLs bypass SSRF validation** — The existing SSRF middleware only validates the initial user-supplied URL at the API entrypoint. Every URL the BFS loop discovers from page content must also pass through `validate_url_for_ssrf()` before being fetched. This is a confirmed CVE class (LangChain RecursiveUrlLoader, CVE-2026-26019). Treat as a pre-merge security gate: trace every code path from link discovery to Playwright fetch.

3. **DOCX font substitution fails silently on Railway** — Railway containers lack Calibri, Cambria, and other common Windows/Office fonts. WeasyPrint substitutes silently and returns HTTP 200 with a visually degraded PDF. For v2.0 scope to content documents and document the limitation prominently. Add Liberation fonts to the Dockerfile (metric-compatible open-source alternatives) for better fidelity.

4. **Crawl enters infinite loop on paginated sites** — Sites with `?page=N` query strings generate unbounded distinct URLs. Enforce both `max_pages` (default 10, max 50) and `max_depth` (default 2, max 5) simultaneously. Normalize URLs before deduplication (strip `utm_*` and other analytics params). Cap the visited-URL set at `max_pages * 5` to prevent unbounded memory growth.

5. **Resend rejects attachments via batch endpoint + base64 size inflation** — Route all emails with attachments through the single-send endpoint. Validate attachment size before encoding: the practical safe maximum is 25MB (not 40MB — base64 encoding inflates by ~33%). The `content` field must be a base64 string, not raw bytes.

## Implications for Roadmap

Based on combined research, the build dependency graph has a clear sequence: domain gates the public site, docs need to be written but don't block backends, the three backend features are independent of each other, and the MCP server update must follow all backends.

### Phase 1: Custom Domain + SSL
**Rationale:** The brand site is currently unreachable from the public internet. Domain + SSL must be live before docs pages can be shared or linked in the npm README. All 5 API reference pages are useless without it. This is also the fastest phase — 5-15 minutes of config work with zero code changes.
**Delivers:** `https://x402.jameswisdom.ink` accessible publicly with auto-renewing SSL. Existing nginx, Playwright, and transcription services are unaffected.
**Implements:** Add ingress rule to `~/.cloudflared/config.yml`, add CNAME in Cloudflare DNS dashboard, set `SITE_URL` env var, rebuild and redeploy Astro site.
**Avoids:** Cloudflare SSL mode pitfall — use Tunnel with HTTP backend, set SSL mode to "Full", do not add HTTP-to-HTTPS redirect in nginx.
**Research flag:** SKIP — zero-research phase. Exact config syntax confirmed against live Cloudflare Tunnel docs and existing transcription tunnel config.

### Phase 2: API Documentation (5 New Reference Pages)
**Rationale:** Pure content work with no backend dependencies other than the domain being live. Can be drafted before Phase 1 completes, deployed after. Filling in all 5 missing API docs converts the site from "partial" to "complete" before any new backend features are advertised.
**Delivers:** Reference pages for scraping, conversion, search, email, and transcription APIs. Each page follows the established template: Overview, Parameters table, curl + MCP tool call examples, error codes, free test endpoint URL.
**Implements:** Update `site/src/content/docs/api-reference.mdx` in place (single-page update, faster to ship; split to separate pages in a future milestone). Update sidebar in `astro.config.mjs`.
**Avoids:** Missing pages from Starlight sidebar — verify each page appears in sidebar before deploy; check that draft pages are hidden in production builds.
**Research flag:** SKIP — well-established patterns from Stripe/Resend/Firecrawl docs conventions, confirmed in features research.

### Phase 3: DOCX-to-PDF Conversion
**Rationale:** Simplest backend feature: one new model class, one new function, one new `elif` branch, one `requirements.txt` addition. No new system dependencies. Validates the Railway redeploy cycle before touching the more complex email and crawl features.
**Delivers:** `x402_convert_file` tool accepts `type: "docx"`, returns PDF as base64. Conversion pipeline: mammoth (DOCX to semantic HTML) then WeasyPrint (HTML to PDF), entirely in-process, reusing existing `safe_url_fetcher` and `run_in_threadpool` patterns.
**Uses:** mammoth 1.12.0 (pure Python, no apt deps), WeasyPrint (already installed), existing `ConvertRequest` discriminated union pattern.
**Avoids:** Font substitution silent failure — test with a Calibri + table DOCX on Railway before merging. Consider adding Liberation fonts to the Dockerfile for better font fidelity.
**Research flag:** SKIP — mammoth API is simple and well-documented. Integration pattern is identical to existing `sync_html_to_pdf()`. The only validation needed is a real-world DOCX test on Railway before declaring done.

### Phase 4: Email Attachments + CC/BCC
**Rationale:** Purely additive Pydantic model change. The Resend SDK already supports all fields at the current version constraint. The only new logic is `build_send_params()` updating and base64 size validation. No new Railway service, no new endpoints, no new packages.
**Delivers:** `x402_send_email` tool accepts `cc`, `bcc`, and `attachments` (base64 content, filename, optional content_type). Attachment size validated at 25MB pre-encoding maximum. Empty attachment array treated same as no attachments.
**Uses:** Resend SDK 2.23.0 (already within version constraint), existing `EmailRequest` model pattern.
**Avoids:** Resend batch endpoint + attachments error (route all attachment emails through single-send); base64 inflation (25MB not 40MB limit); raw bytes vs string encoding issue (`base64.b64encode(data).decode("utf-8")`).
**Research flag:** SKIP — Resend attachment API confirmed against official reference. Pydantic model extension follows existing patterns exactly.

### Phase 5: Multi-Page Site Crawl
**Rationale:** Most complex backend feature — stateful BFS loop, Railway timeout risk, security considerations. Builds on the validated Railway deploy cycle from Phases 3 and 4. By this point the team has confirmed redeploy is working and the MCP server pattern is ready for a new tool.
**Delivers:** New `x402_crawl_site` tool (12th MCP tool). `POST /crawl` endpoint on the scraping service. BFS crawl from a seed URL, same-domain only by default, max 15 pages synchronous for v2.0. Returns array of per-page scrape results in the same schema as `/scrape`. `GET /crawl/test` returns a fixture.
**Uses:** crawlee[playwright] 1.5.0 (verify vs pinned `playwright==1.44.0`), existing `scrape_page()` / `extract_content()` / `validate_url_for_ssrf()` functions. New `fixture_crawl.json` for the free test endpoint.
**Avoids:** SSRF bypass on discovered URLs — `validate_url_for_ssrf()` must be called at the fetch layer for every URL, not just the API entrypoint. `max_pages=15` synchronous cap to stay under Railway 60s timeout. URL normalization before deduplication. Filter links to `http://` and `https://` schemes only before queueing.
**Research flag:** NEEDS ATTENTION during implementation. Two pre-merge checks required: (1) crawlee 1.5.0 vs `playwright==1.44.0` version compatibility check against crawlee's pyproject.toml; (2) SSRF validation coverage code review on all discovered-URL code paths. Consider async job pattern (job_id + polling) as immediate follow-on once synchronous crawl is validated.

### Phase 6: MCP Server Update + npm Publish
**Rationale:** Hard dependency on all three backend phases being deployed and tested. The MCP server is the public-facing npm package; publish only after integration tests pass in both free and paid modes.
**Delivers:** Updated `src/index.ts` with `x402_crawl_site` tool, updated `x402_send_email` Zod schema (cc/bcc/attachments), updated `x402_convert_file` type enum (add "docx"). npm publish v2.0.0.
**Uses:** Existing `apiPost` / `apiGet` helper pattern, Zod validation patterns from all 11 existing tools.
**Avoids:** Publishing before backend endpoints are deployed (MCP tool calls will 404 until Railway redeploys are live).
**Research flag:** SKIP — follows established patterns for all 11 existing tools. New tool and schema additions are mechanical.

### Phase Ordering Rationale

- **Domain before everything:** The site is publicly unreachable until Phase 1 is complete. All docs links are dead until then. The `SITE_URL` must be set correctly before the Astro build for canonical URLs and OG tags to work.
- **Docs before backends:** Docs can be written and deployed as soon as the domain is live, independently of backend development. Getting docs live early means any users who discover the npm package during v2.0 development see complete reference pages rather than gaps.
- **DOCX before email before crawl:** Ascending complexity order. DOCX validates Railway redeploys. Email validates Pydantic model extension patterns. Crawl adds new complexity (BFS loop, security, timeout risk) and benefits from a proven deploy cycle.
- **MCP server last:** `src/index.ts` is the integration point. It should reference endpoints that already exist and have been verified. Publish after integration testing all tool paths in both free and paid modes.
- **Parallel work is possible:** Phases 3, 4, and 5 are independent of each other (different Railway services, different files). They can be developed simultaneously; the sequencing above is the recommended order for a single developer but can be parallelized with no conflicts.

### Research Flags

Phases needing extra attention during implementation:

- **Phase 5 (Crawl):** Verify crawlee 1.5.0 vs pinned `playwright==1.44.0` compatibility before writing any crawl code (check crawlee's `pyproject.toml` for its playwright constraint). Run a dedicated SSRF security review: trace every code path from link discovery to Playwright fetch and confirm `validate_url_for_ssrf()` is called on each. Budget time for the async job pattern as an immediate follow-on if synchronous crawl proves too slow or hits the Railway 60s ceiling.
- **Phase 3 (DOCX):** Test with a real-world DOCX containing Calibri font and tables on Railway before merging. Decide before implementation whether to add Liberation fonts to the Dockerfile.

Phases with standard well-documented patterns (skip research-phase):

- **Phase 1 (Domain/SSL):** Cloudflare Tunnel ingress rule pattern is confirmed and already in use for transcription service. Exact config syntax is in STACK.md.
- **Phase 2 (Docs):** Starlight MDX page creation and sidebar config are standard, already in use for existing 3 docs pages.
- **Phase 4 (Email):** Resend attachment API confirmed against official reference. Pydantic model extension follows existing patterns.
- **Phase 6 (MCP publish):** Follows established patterns from all 11 existing tools.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified against PyPI/npm. mammoth v1.12.0 confirmed March 12, 2026. crawlee v1.5.0 confirmed March 6, 2026. Resend 2.23.0 confirmed Feb 23, 2026. One gap: crawlee vs `playwright==1.44.0` version compatibility — must verify before Phase 5 implementation. |
| Features | HIGH | Resend CC/BCC/attachment API confirmed against official docs. Cloudflare Tunnel ingress confirmed. Astro/Starlight sidebar config confirmed. Key resolution: FEATURES.md initially recommended LibreOffice; STACK.md overrides with the superior mammoth approach (zero Docker cost). Decision: use mammoth. |
| Architecture | HIGH | All integration points verified against live source code. Discriminated union pattern, `scrape_page()` reuse, `safe_url_fetcher`, `run_in_threadpool` patterns all confirmed in actual code. Build order derived from dependency analysis of actual files. |
| Pitfalls | HIGH (Cloudflare SSL, crawl SSRF, Resend limits), MEDIUM (DOCX font substitution, Starlight nav) | Cloudflare SSL loop, SSRF bypass, and Resend batch/attachment error are confirmed with official sources or CVE documentation. Font substitution severity on Railway needs empirical validation. |

**Overall confidence:** HIGH

### Gaps to Address

- **Crawlee vs Playwright version compatibility:** `crawlee[playwright]>=1.5.0` may require a Playwright version newer than pinned `playwright==1.44.0`. Check crawlee's `pyproject.toml` for its Playwright constraint before writing any crawl code. If incompatible, relax the pin to `playwright>=1.44.0` or let crawlee resolve. Low-risk gap but must be resolved first in Phase 5.

- **DOCX font fidelity on Railway:** Research confirms the problem class exists but severity on actual Railway containers is unknown without empirical testing. The fix (add Liberation fonts to the Dockerfile) is low-cost. Decide during Phase 3 implementation after testing a real-world DOCX on Railway.

- **Crawl x402 pricing model:** FEATURES.md flags that per-page USDC micropayment for crawl requires careful design because x402's per-request model is designed for single calls. For v2.0 the simplest approach is a flat $0.05 per crawl job (confirmed in architecture research as `@pay("$0.05")`). Per-page pricing is a v2.x design challenge.

- **Async job pattern for crawl:** The synchronous implementation with `max_pages=15` is the v2.0 approach. Users who want to crawl 50+ pages will need the async job pattern (POST to job_id, GET status). Flagged as a v2.x follow-on. Architecture research contains the full design; it was intentionally deferred to validate the core extraction logic first.

## Sources

### Primary (HIGH confidence)
- `x402-scraping-api/main.py` (live source) — SSRF middleware, `scrape_page()`, `extract_content()`, `@pay()` pattern
- `x402-email-api/main.py` (live source) — `EmailRequest`, `build_send_params()`, `check_and_increment_wallet_limit()`
- `x402-conversion-api/main.py` (live source) — discriminated union, `sync_html_to_pdf()`, `safe_url_fetcher`, `run_in_threadpool`
- `src/index.ts` (live source) — APIS dict, `apiPost`/`apiGet` helpers, Zod patterns, all 11 tool definitions
- `site/astro.config.mjs` (live source) — `SITE_URL` env var pattern, sidebar structure
- [resend.com/docs/api-reference/emails/send-email](https://resend.com/docs/api-reference/emails/send-email) — CC/BCC/attachments confirmed
- [developers.cloudflare.com](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) — CNAME auto-creation, multiple ingress rules, SSL termination
- [pypi.org/project/crawlee](https://pypi.org/project/crawlee/) — v1.5.0 confirmed March 6, 2026
- [pypi.org/project/mammoth](https://pypi.org/project/mammoth/) — v1.12.0 confirmed March 12, 2026
- [npmjs.com/package/@astrojs/starlight](https://www.npmjs.com/package/@astrojs/starlight) — 0.37.6 latest; already at current version

### Secondary (MEDIUM confidence)
- Firecrawl crawl API docs — crawl endpoint patterns, max_depth / include_paths / exclude_paths conventions
- Cloudflare Browser Rendering /crawl API (March 2026) — competitive feature comparison
- LangChain SSRF CVE-2026-26019 — SSRF bypass via discovered URL validation failure pattern
- Aspose DOCX font handling on Linux — font substitution behavior and Liberation fonts as fix
- OWASP SSRF prevention cheat sheet — URL normalization requirements before validation

### Tertiary (LOW confidence — needs validation)
- crawlee 1.5.0 vs `playwright==1.44.0` version compatibility — not confirmed; must check crawlee's pyproject.toml before Phase 5 implementation
- Actual font substitution severity on Railway containers — confirmed problem class, severity unknown without empirical test on Railway Debian base image

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
