# Roadmap: x402 API Network

## Milestones

- **v1.0 npm Publish + Brand Site** — Phases 1-4 (shipped 2026-03-12)
- **v1.1 Universal Utility APIs** — Phases 5-10 (in progress)

## Phases

<details>
<summary>v1.0 npm Publish + Brand Site (Phases 1-4) — SHIPPED 2026-03-12</summary>

- [x] Phase 1: Package Hardening + Input Validation (2/2 plans) — 2026-03-09
- [x] Phase 2: npm Publish (1/1 plan) — 2026-03-10
- [x] Phase 3: Brand Site Build (4/4 plans) — 2026-03-11
- [x] Phase 4: Deployment (2/2 plans) — 2026-03-12

See [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

---

### v1.1 Universal Utility APIs (Phases 5-10)

**Goal:** Add 5 new APIs to the x402 network. Expand from 3 to 8 backend services and from 6 to 11 MCP tools. All new tools follow the same stateless, sub-$0.10, free-test-endpoint pattern as v1.0.

**Build order rationale:** Scraping first (highest-risk unknown — Playwright/Chromium in Railway container); file conversion second (reuses Playwright knowledge, no API keys); search third (thin Tavily wrapper, low complexity); email fourth (start DNS setup during Phase 7 to absorb 48-hour SPF/DKIM propagation delay); transcription fifth (most infrastructure — custom x402 middleware, nginx, launchd on home server); MCP update last (all service URLs must be known before wiring `src/index.ts`).

---

#### Phase 5: Web Scraping API

**Status:** COMPLETE (2026-03-12)
**Requirements:** SCRAPE-01, SCRAPE-02, SCRAPE-03, SCRAPE-04, SCRAPE-05
**Production URL:** https://x402-scraping-api-production.up.railway.app
**Plans:** 2/2 plans complete

Plans:
- [x] 05-01-PLAN.md — Build complete scraping service (main.py, Dockerfile, config, fixture)
- [x] 05-02-PLAN.md — Docker validation, Railway deployment, production verification

**What ships:** A new Railway service (`x402-scraping-api`) that accepts a URL and returns structured JSON — markdown-converted page text, extracted links, tables, and page metadata. JS-rendered pages are supported via Playwright. A `wait_for` CSS selector param allows callers to pause until async SPA content loads. SSRF protection validates resolved IPs against private/loopback ranges before any outbound fetch.

**Key constraints:**
- Docker base image: `mcr.microsoft.com/playwright/python:v1.44.0-jammy` (Chromium system deps required — never Alpine or -slim)
- One persistent browser instance per FastAPI process (lifespan startup event); new page per request, close page not browser
- Railway service memory: 1GB minimum (Chromium is 200-400MB per instance)
- SSRF: resolve hostname → `ipaddress.ip_address(ip).is_private` before `requests.get(user_url)`
- Free test endpoint: returns fixture data for a fixed allowlisted domain — no live scraping

**Success criteria:**
1. A developer calls the free test endpoint with a fixture URL and receives a JSON response containing `title`, `markdown`, `links`, `tables`, and `metadata` fields — no auth or USDC required
2. A paid call to a JS-rendered SPA URL (e.g., a React app) returns populated `markdown` content, confirming Playwright executed JavaScript before extraction
3. A call with `wait_for: ".product-price"` blocks until the CSS selector appears, returning accurate product data rather than the loading skeleton
4. A call with a private IP URL (e.g., `http://10.0.0.1/`) returns a 400 error with an SSRF rejection message — the request never leaves the container
5. The Railway service deploys from a clean repo push with no manual Chromium installation steps — the Docker base image handles all system deps

---

#### Phase 6: File Conversion API

**Status:** COMPLETE (2026-03-13)
**Requirements:** CONV-01, CONV-02, CONV-03, CONV-04, CONV-05
**Production URL:** https://x402-conversion-api-production.up.railway.app
**Plans:** 2/2 plans complete

**What ships:** A new Railway service (`x402-conversion-api`) with three conversion operations unified under one endpoint: image resize/reformat (Pillow), CSV-to-JSON (Python stdlib), and HTML-to-PDF (WeasyPrint). Input is a URL pointing to the source file plus the target format. Output is base64-encoded with a MIME type header. DOCX-to-PDF is explicitly deferred to v1.2 (LibreOffice adds ~300MB to the Docker image).

**Key constraints:**
- SSRF validation on all input URLs (same `ipaddress.is_private` check as Phase 5)
- 10MB file size limit enforced before processing
- `TemporaryDirectory` cleanup pattern — no temp files left on disk after request
- WeasyPrint requires Python >= 3.10 and system Cairo/Pango libs in Dockerfile
- Free test endpoint: returns fixture output (resized placeholder image, sample CSV-to-JSON, sample HTML-to-PDF)

**Success criteria:**
1. A developer calls the free test endpoint and receives base64-encoded fixture output for each supported format (image, CSV, HTML) — no USDC required
2. A paid call submitting a PNG URL with `target_format: "jpeg"` and `width: 400` returns a base64 JPEG at the requested width with correct MIME type `image/jpeg`
3. A paid call submitting a CSV URL returns valid JSON with auto-detected headers as keys and each data row as an object
4. A paid call submitting an HTML URL returns a base64-encoded PDF that renders the HTML content correctly (WeasyPrint path confirmed working in Railway container)
5. A call submitting a URL resolving to a private IP returns a 400 SSRF rejection — the file fetch never executes

---

#### Phase 7: Web Search API

**Status:** COMPLETE (2026-03-14)
**Requirements:** SEARCH-01, SEARCH-02, SEARCH-03, SEARCH-04, SEARCH-05
**Production URL:** https://x402-search-api-production.up.railway.app
**Plans:** 2/2 plans complete

Plans:
- [x] 07-01-PLAN.md — Build complete search service (main.py, Dockerfile, config, fixture)
- [x] 07-02-PLAN.md — Docker validation, Railway deployment, production verification

**What ships:** A new Railway service (`x402-search-api`) wrapping the Tavily search API. Accepts a query string and returns ranked results (title, URL, snippet, relevance score). `include_answer` requests a Tavily-synthesized direct answer alongside results. `include_domains`/`exclude_domains` filter results to specific sources. Per-wallet daily query limit prevents cost spikes.

**Key constraints:**
- Backend: Tavily (`tavily-python ^0.5.x`), $0.008/query, 1,000 free credits/month
- `TAVILY_API_KEY` set as Railway env var — never hardcoded
- Per-wallet rate limit: 50 queries/day enforced in FastAPI middleware
- Set a Tavily billing alert before deploying to production
- Free test endpoint: returns fixture search results for a fixed query — no live Tavily call

**Action during this phase:** Configure Resend verified sender domain DNS records (SPF/DKIM/DMARC) in parallel to absorb the 48-hour propagation window before Phase 8 begins.

**Success criteria:**
1. A developer calls the free test endpoint and receives fixture JSON with `results` array containing `title`, `url`, `snippet`, and `score` fields — no USDC required
2. A paid call with `query: "x402 protocol"` returns at least 3 ranked results with populated titles, real URLs, and non-empty snippets
3. A paid call with `include_answer: true` returns an `answer` field containing a synthesized summary above the results array
4. A paid call with `include_domains: ["docs.python.org"]` returns only results from the specified domain
5. A wallet that exceeds 50 queries/day receives a 429 rate-limit response on the 51st call

---

#### Phase 8: Email Sending API

**Status:** COMPLETE (2026-03-14)
**Requirements:** EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05
**Production URL:** https://x402-email-api-production.up.railway.app
**Plans:** 2/2 plans complete

**What ships:** A new Railway service (`x402-email-api`) that sends transactional email via the Resend SDK. Accepts `to`, `subject`, and a body (plain text or HTML; plain-text fallback auto-generated from HTML). Returns a Resend message ID as delivery confirmation. Sender domain is hardcoded to the verified domain; per-wallet daily send limit prevents abuse.

**Key constraints:**
- DNS prerequisite: SPF/DKIM/DMARC records must be verified on Resend before any code is deployed (start during Phase 7 — 48-hour propagation)
- Sender domain: fixed verified domain; `from` address not user-configurable
- Per-wallet rate limit: 10 sends/day enforced in FastAPI layer
- Log every send event: wallet address, recipient domain (not full address), subject hash — for abuse review
- Free test endpoint: sandbox mode — logs the send, returns a fake message ID, no real delivery via Resend

**Success criteria:**
1. A developer calls the free test endpoint with `to`, `subject`, and `body` and receives a fake message ID response — no real email is sent, no USDC required
2. A paid call with a plain-text `body` results in a delivered email and returns a Resend message ID (verifiable via Resend dashboard)
3. A paid call with an HTML `body` is delivered with correct HTML rendering; the auto-generated plain-text fallback is present in the email headers
4. A wallet that sends 11 emails in one day receives a 429 rate-limit response on the 11th call — the email is not sent
5. Resend rejects a send attempt using an unverified sender domain — the FastAPI service returns a descriptive 500 error rather than an opaque crash

---

#### Phase 9: Audio Transcription API

**Status:** In Progress (1/2 plans complete)
**Requirements:** TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05, TRANS-06
**Plans:** 2/2 plans complete

Plans:
- [x] 09-01-PLAN.md — Build complete transcription service (main.py, config.py, requirements.txt) — 2026-03-15
- [ ] 09-02-PLAN.md — Home server deployment, Cloudflare Tunnel setup, production verification

**What ships:** A self-hosted FastAPI service on the home Mac server (10.0.0.2, macOS Monterey, Intel x86_64) at port 8889. Accepts an audio file URL, downloads it, and transcribes via `faster-whisper` with `compute_type="int8"`. Returns transcript text, detected language, and optional word-level segment timestamps. Payment gated via `fastapi-x402` (same pattern as Railway services). Cloudflare Tunnel provides public access at `transcribe.jameswisdom.ink`. A launchd plist persists the process across reboots.

**Key constraints:**
- `faster-whisper ^1.2.1` with `compute_type="int8"` — MLX Whisper is Apple Silicon only and will not install on x86_64 (confirm with `uname -m` before installing)
- `ffmpeg` installed via Homebrew — required by faster-whisper for audio decoding
- Custom x402 middleware: validate `X-PAYMENT` header against `https://x402.org/facilitator/verify` — match the exact header/response format that `x402-fetch` on the MCP side expects
- File size limit: 25MB; duration limit: 10 minutes (ffprobe check before transcription)
- 300-second subprocess timeout on the transcription call
- SSRF validation on the input audio URL
- launchd plist at `~/Library/LaunchAgents/com.x402.transcription.plist`
- Public accessibility: configure router port forwarding (or Cloudflare Tunnel if ISP blocks inbound) — the `src/index.ts` APIS entry must use a public URL, not `10.0.0.2`
- Free test endpoint: returns fixture transcript for a fixed audio URL — no live transcription

**Success criteria:**
1. A developer calls the free test endpoint and receives fixture JSON with `transcript`, `language`, and `segments` fields — no USDC required
2. A paid call with a 2-minute English audio URL returns a populated transcript within 300 seconds, with `language: "en"` detected automatically
3. A paid call with `word_timestamps: true` returns segments with `start`, `end`, and `text` fields per word
4. A paid call with `language: "es"` (Spanish hint) skips language detection and transcribes in the specified language
5. A call with an audio file exceeding 25MB or 10 minutes receives a 400 error with the specific limit stated — no partial transcription is attempted
6. The launchd service survives a home server reboot: the API is reachable at its port within 60 seconds of login without manual intervention

---

#### Phase 10: MCP Server Update + npm Publish

**Status:** Planning Complete
**Requirements:** MCP-01, MCP-02, MCP-03
**Plans:** 2/2 plans complete

Plans:
- [ ] 10-01-PLAN.md — Add 4 APIS entries, 4 new tools, review email consistency, reduce health timeout, bump version, update README and package.json metadata
- [ ] 10-02-PLAN.md — Build, verify artifact, npm publish as 1.1.0, post-publish verification, git tag v1.1.0

**What ships:** `src/index.ts` updated with 5 new tool registrations and 5 new APIS dict entries. All production service URLs (from Phases 5-9) are wired in. `x402_network_info` health check expanded to cover all 8 APIs. Version bumped to `1.1.0`. Package published as `x402-mcp-server@1.1.0` on npm.

**Key constraints:**
- Do not hardcode any service URLs until all Railway services and the transcription service have production URLs
- Each new tool follows the existing `apiGet`/`apiPost` helper pattern in `src/index.ts`
- Zod validation on all user-facing params for all 5 new tools
- Integration test: all 11 tools callable in free mode (no USDC) before `npm publish`
- Transcription tool description must state expected latency (50-100 seconds for 5-minute audio) and the 25MB/10-minute limits

**Success criteria:**
1. `npx -y x402-mcp-server@1.1.0` starts without errors and registers 11 tools visible in the MCP client's tool list
2. All 5 new tools are callable in free mode and return the fixture responses from their respective test endpoints — no USDC wallet required
3. `x402_network_info` returns health status for all 8 APIs with accurate endpoint URLs
4. `npm pack --dry-run` shows no secret files (no `.env`, no `*key*`, no credential files) in the published artifact
5. The published `1.1.0` package on npm has an accurate README listing all 11 tools with correct parameter descriptions and pricing

---

*Roadmap created: 2026-03-09*
*Last updated: 2026-03-15 — Phase 10 planned (2 plans in 2 waves). Plan 01: source + docs update (Wave 1). Plan 02: build + publish + tag (Wave 2).*
