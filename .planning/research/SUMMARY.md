# Project Research Summary

**Project:** x402 MCP Server — v1.1 Universal Utility APIs
**Domain:** Micropayment-gated API services (web scraping, email, search, file conversion, audio transcription)
**Researched:** 2026-03-12
**Confidence:** HIGH

## Executive Summary

The v1.1 milestone adds five new utility APIs to the existing x402 MCP server, following the proven Railway/FastAPI/fastapi-x402 pattern from v1.0. Four of the five new services (scraping, email, search, file conversion) are straightforward extensions of the existing architecture — new Railway services using the same Python/FastAPI deployment pattern, each independently deployable. The fifth (audio transcription) has a fundamentally different deployment model: a self-hosted FastAPI service on a home Mac server at 10.0.0.2, using `faster-whisper` (not MLX Whisper) due to the Intel x86_64 architecture of that machine.

The key strategic decision confirmed by research is Tavily for web search: $0.008/query PAYG with 1,000 free credits/month, LLM-ready structured output, and no subscription trap. The key technical finding is that MLX Whisper is Apple Silicon only and will not install on the home server — `faster-whisper` with `compute_type="int8"` is the correct substitute, with comparable accuracy and 4x better CPU performance than `openai-whisper`. For file conversion, DOCX-to-PDF via LibreOffice adds ~300MB to the Docker image and should be deferred to v1.2 — ship image resize, CSV-to-JSON, and HTML-to-PDF (via Playwright, already in the stack) first.

The main risks are security and abuse: SSRF validation is required on every URL-fetch endpoint (scraping, file conversion, transcription), Resend requires a verified domain and enforces strict abuse limits (10 sends/day per wallet is the recommended internal cap), and the transcription service is LAN-only unless port-forwarded, which makes it unusable for external agents in the npm-published package.

## Key Findings

### Recommended Stack

Four Railway services use identical boilerplate — Python 3.11, FastAPI, `fastapi-x402` middleware, one `requirements.txt` per service, Procfile + optional Dockerfile for system deps. No new npm dependencies in the MCP server itself; the five new tools follow the existing `apiGet`/`apiPost` helper pattern.

The transcription service diverges: it runs on the home Mac server (macOS Monterey, Intel x86_64), uses `faster-whisper` for CPU inference, requires a hand-rolled x402 middleware (not `fastapi-x402`, which is untested on macOS), nginx on port 8889 (existing nginx serves port 8888), and a launchd plist for process persistence across reboots.

**Core technologies:**
- `faster-whisper ^1.2.1`: audio transcription on Intel CPU — CTranslate2-based, 4x faster than openai-whisper at same accuracy, explicit x86_64 support via int8 quantization. MLX Whisper is Apple Silicon only and will not install on x86_64.
- `tavily-python ^0.5.x`: web search backend — 1,000 free credits/month, $0.008/query PAYG, returns LLM-ready structured JSON (title, url, content, score). No subscription required.
- `playwright ^1.58.0` (Python): shared between the scraping API and HTML-to-PDF conversion — already planned for scraping, so HTML-to-PDF comes for free.
- `WeasyPrint ^68.1`: HTML-to-PDF pure Python alternative — lighter than Playwright for simple HTML. Python >=3.10 required.
- `Pillow ^12.1.1`: image resize and format conversion — all image operations in one library.
- `resend ^2.x`: transactional email via Resend SDK — type-hinted SDK 2.0, simple `resend.Emails.send()` pattern.
- LibreOffice (system dep via apt): DOCX-to-PDF — ~300MB Docker image addition, 8-second headless startup. Defer to v1.2.
- MCP server (`src/index.ts`): no new npm dependencies — add 5 entries to the `APIS` dict and 5 `server.tool()` blocks, bump version to `1.1.0`.

### Expected Features

Each API has a focused surface: one primary action, a small parameter set, and clean structured JSON output. The pattern is URL/query in, structured data out — never raw HTML, never embedded binary blobs.

**Must have (table stakes):**
- Scraping: URL → `{title, markdown, links[], tables[], metadata, status_code}` — users expect clean content extraction, not raw HTML
- Email: `to/subject/html` → `{id, status}` — delivery confirmation is non-negotiable; Resend message ID proves it
- Search: query → `{results[{title, url, snippet, score}]}` — relevance ordering and real destination URLs expected
- File conversion: `input_url + output_format` → base64 output with MIME type — unified interface across all supported conversions
- Transcription: audio URL → `{transcript, language, segments[]}` — language detection and segment timing are standard Whisper output

**Should have (competitive):**
- Scraping: `wait_for` CSS selector (handles async data loads), `only_main_content` stripping (LLM-ready by default)
- Search: `include_answer` boolean — Tavily synthesizes a direct answer above results in one call; `search_depth` basic/advanced
- File conversion: image resize + format conversion in a single call; CSV-to-JSON with auto-header detection
- Transcription: word-level timestamps (`word_timestamps: true`), language hint parameter, confidence scores per segment

**Defer (v1.2+):**
- DOCX-to-PDF — LibreOffice adds 300MB to Docker image; ship image/CSV/HTML-to-PDF first, add DOCX once Dockerfile pattern is proven
- Structured JSON extraction for scraping (LLM-schema fill) — expensive, requires LLM call per scrape
- Speaker diarization for transcription — separate model, significant complexity
- Email attachments — viable but adds multipart/base64 complexity
- Whisper model selection (tiny/base/large tiers) — expose after basic flow is validated

### Architecture Approach

The system follows two deployment patterns: (1) four independent Railway services using the proven FastAPI + `fastapi-x402` middleware pattern, each with its own `requirements.txt` and Dockerfile; and (2) one self-hosted FastAPI service on the home Mac at 10.0.0.2, using hand-rolled x402 middleware, nginx reverse proxy on port 8889, and a launchd plist for process lifecycle. The MCP server's `src/index.ts` gains five new entries in the `APIS` dict and five `server.tool()` blocks — no structural changes to the MCP layer until the file exceeds ~600 lines.

**Major components:**
1. `src/index.ts` (modified) — adds 5 new tool registrations to the APIS dict; grows from 6 to 11 tools; version bumped to 1.1.0
2. Railway services x4 (new) — scraping, email, search, file conversion; each independently deployed; same FastAPI/fastapi-x402 boilerplate; one service per API to prevent dependency bleed
3. Home server transcription (new) — FastAPI + faster-whisper + custom x402 middleware at `http://10.0.0.2:8889`; nginx proxy; launchd plist; LAN-only unless port-forwarded

### Critical Pitfalls

1. **MLX Whisper on Intel Mac** — `pip install mlx` silently fails or produces cryptic import errors on x86_64. Use `faster-whisper` with `compute_type="int8"`. Verify with `uname -m` before writing any transcription code.

2. **Playwright missing system deps in Railway containers** — `playwright install chromium` downloads the binary but not its system library dependencies. Use `mcr.microsoft.com/playwright/python:v1.44.0-jammy` as the Docker base image or run `playwright install-deps chromium` in the Dockerfile. Never use Alpine or `-slim` variants for Playwright services.

3. **SSRF on URL-fetch endpoints** — scraping, file conversion, and transcription all accept user-supplied URLs. Without IP validation, agents can probe Railway's internal network and exfiltrate env vars. Validate with `ipaddress.ip_address(resolved_ip).is_private` before any `requests.get(user_url)` on the FastAPI backend. Zod `.url()` on the MCP side is necessary but insufficient.

4. **Resend domain verification + abuse limits** — Resend hard-rejects unverified sender domains. Configure SPF/DKIM/DMARC DNS records before writing any code (up to 48-hour propagation delay). Enforce 10 sends/day per wallet address in the FastAPI layer to prevent the service becoming a spam cannon; Resend account suspension is non-recoverable for domain reputation.

5. **LibreOffice in Railway containers** — ~500MB installed size, 8-second headless startup per cold start. Pre-warm with a dummy conversion in the FastAPI `lifespan` startup event. Defer DOCX-to-PDF entirely to v1.2 and ship the three lighter conversions (image, CSV, HTML-to-PDF) in v1.1.

6. **Home server transcription LAN-only** — `http://10.0.0.2:8889` is unreachable from outside the local network. Users who install the npm package from outside the LAN will get `ECONNREFUSED` on every transcription call. Configure router port forwarding and update the URL in `src/index.ts` to a public hostname before publishing 1.1.0.

7. **Playwright memory exhaustion** — each Chromium instance is 200-400MB. Launch one browser at FastAPI startup (lifespan event), create a new page per request, close the page (not the browser). Set Railway service memory to at least 1GB.

## Implications for Roadmap

Based on research, the recommended build order is: scraping → file conversion → search → email → transcription → MCP update → npm publish.

### Phase 1: Web Scraping API
**Rationale:** Playwright in a Railway container is the highest-risk unknown. Proving Chromium launches correctly in the Docker environment validates the base for both scraping and HTML-to-PDF conversion. Build this first to surface container issues early.
**Delivers:** `x402_scrape` tool — URL to structured JSON (markdown, links, tables, metadata); free test endpoint with allowlisted domains
**Addresses:** URL-to-content extraction (high-value, high-agent-demand), JS-rendered SPA support
**Avoids:** Pitfalls 2 (Playwright system deps), 3 (Playwright OOM), 4 (anti-bot detection), SSRF, timeout cascade

### Phase 2: File Conversion API (image + CSV + HTML-to-PDF)
**Rationale:** Most self-contained — no third-party API keys needed, Playwright is already proven from Phase 1, Pillow and csv stdlib are trivial. Ship image resize, CSV-to-JSON, and HTML-to-PDF. Explicitly skip DOCX-to-PDF (LibreOffice) for this phase.
**Delivers:** `x402_convert_file` tool — image resize/reformat, CSV-to-JSON, HTML-to-PDF; base64 output
**Uses:** Pillow, WeasyPrint, csv stdlib, Playwright (shared Docker image pattern from Phase 1)
**Implements:** `TemporaryDirectory` cleanup pattern, SSRF validation, 10MB file size limit

### Phase 3: Web Search API
**Rationale:** Thin wrapper over Tavily — one SDK call, normalize response. Research confirmed: Tavily at $0.008/query, 1,000 free credits/month, no credit card for dev tier, LLM-ready output.
**Delivers:** `x402_search` tool — query to ranked results with title, URL, snippet, score; `include_answer` support
**Uses:** `tavily-python ^0.5.x`, Tavily API key as Railway env var
**Implements:** Per-wallet rate limiting (50 queries/day), provider billing alert configured at Tavily dashboard

### Phase 4: Email Sending API
**Rationale:** Requires Resend account + DNS verification before writing any code. DNS propagation can take 48 hours — start DNS setup in parallel with Phase 3. Build is LOW complexity once domain is verified.
**Delivers:** `x402_email_send` tool — transactional email with delivery confirmation (Resend message ID)
**Uses:** `resend ^2.x` SDK, fixed verified sender domain, hardcoded from-address
**Implements:** 10 sends/day per wallet rate limit, plain-text/Markdown body only (no HTML), logging of send events (wallet, recipient domain, subject hash)

### Phase 5: Audio Transcription API (home server)
**Rationale:** Most infrastructure work of the five APIs. Build last so x402 middleware patterns are understood from Railway implementations. faster-whisper confirmed correct for Intel x86_64 with `compute_type="int8"`.
**Delivers:** `x402_transcribe` tool — audio URL to transcript with language detection, segment timing, confidence scores
**Uses:** `faster-whisper ^1.2.1` with `compute_type="int8"`, `ffmpeg` (brew install), nginx port 8889, launchd plist at `~/Library/LaunchAgents/com.x402.transcription.plist`
**Implements:** 25MB file size limit, 10-minute duration limit (ffprobe check), 300-second subprocess timeout, SSRF validation, router port forwarding for public accessibility

### Phase 6: MCP Server Update + npm publish
**Rationale:** All five service URLs must be known before wiring up `src/index.ts`. Integration and publishing step.
**Delivers:** `x402-mcp-server@1.1.0` on npm — 11 tools (6 existing + 5 new), updated `x402_network_info` health check, accurate tool descriptions with enforced limits stated
**Implements:** 5 new APIS dict entries, 5 new `server.tool()` blocks, version bump to `1.1.0`, integration test (all 11 tools, free + paid mode), `npm publish`

### Phase Ordering Rationale

- Scraping comes first because Playwright container compatibility is the highest-risk unknown; proving it early de-risks HTML-to-PDF in Phase 2
- File conversion comes second because it is self-contained (no API keys) and reuses Phase 1's Docker patterns
- Search and email are sequenced to account for Resend's DNS propagation delay — starting DNS setup in parallel with Phase 3 means the domain is verified by Phase 4 build time
- Transcription is last because it has the most infrastructure steps (custom middleware, nginx, launchd, port forwarding) and benefits from seeing the x402 payment flow in Railway services first
- MCP update is deliberately last — no hardcoded URLs until all services have production Railway URLs

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (scraping):** Playwright Chromium launch in Railway Nixpacks environment — requires a `nixpacks.toml` or Dockerfile override; test locally with `docker build && docker run` before Railway deploy
- **Phase 5 (transcription):** Custom x402 middleware correctness — the `X-Payment-Required` response header format and facilitator verify endpoint (`https://x402.org/facilitator/verify`) must match what `x402-fetch` expects on the MCP server side; validate against existing Railway services before relying on it
- **Phase 5 (transcription):** Public accessibility — router port forwarding and dynamic DNS are home-network-specific; may require Cloudflare Tunnel if ISP blocks inbound connections

Phases with standard patterns (skip research-phase):
- **Phase 3 (search):** Tavily SDK is well-documented; the integration is a thin wrapper
- **Phase 4 (email):** Resend SDK 2.0 is documented; the only pre-step is DNS verification
- **Phase 6 (MCP update):** Follows identical pattern to the existing 6 tools; no new patterns needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library choices verified against PyPI; version compatibility confirmed; MLX exclusion on x86_64 verified against MLX repo platform markers |
| Features | HIGH | Feature set validated against Firecrawl, Tavily, Resend, Deepgram/AssemblyAI; competitor analysis confirms table-stakes vs differentiators |
| Architecture | HIGH | Extends proven pattern from v1.0 Railway services; home server pattern is novel but well-understood (FastAPI + nginx + launchd are standard) |
| Pitfalls | HIGH | Pitfalls derived from v1.0 post-mortems + documented Railway/Playwright/LibreOffice community issues; SSRF and abuse patterns are well-documented threat categories |

**Overall confidence:** HIGH

### Gaps to Address

- **Resend verified sender domain:** DNS records must be provisioned before Phase 4 code is written. Start during Phase 3. If `x402.network` is not owned, identify the actual domain to use.
- **Public URL for home server transcription:** The `src/index.ts` APIS dict entry for transcription will contain a hardcoded URL. That URL must be reachable from any MCP client. Confirm port forwarding + dynamic DNS (or Cloudflare Tunnel) works before publishing 1.1.0.
- **Playwright Nixpacks config:** `nixpacks.toml` or Dockerfile override needed for Chromium system deps on Railway. Exact config needs validation during Phase 1 — it is the primary unknown in the entire v1.1 build.
- **faster-whisper CPU performance on home server:** Transcription latency for 5-minute audio on the Intel CPU is estimated at ~10-20x real-time (i.e., 50-100 seconds). Within the 300-second subprocess timeout but may feel slow. Document the latency expectation in the tool description.

## Sources

### Primary (HIGH confidence)
- [pypi.org/project/faster-whisper](https://pypi.org/project/faster-whisper/) — v1.2.1, CTranslate2 x86_64 support, int8 compute type confirmed
- [github.com/ml-explore/mlx](https://github.com/ml-explore/mlx) — arm64 platform markers only; x86_64 install confirmed to fail
- [pypi.org/project/weasyprint](https://pypi.org/project/weasyprint/) — v68.1, Python >=3.10 required
- [pypi.org/project/pillow](https://pypi.org/project/pillow/) — v12.1.1 released Feb 11, 2026
- [pypi.org/project/playwright](https://pypi.org/project/playwright/) — v1.58.0, Python >=3.9
- [pypi.org/project/resend](https://pypi.org/project/resend/) — SDK 2.0, type hints, `resend.Emails.send()` pattern
- [pypi.org/project/tavily-python](https://pypi.org/project/tavily-python/) — confirmed latest Feb 2026; structured LLM-ready output
- [docs.tavily.com/documentation/api-credits](https://docs.tavily.com/documentation/api-credits) — 1,000 free credits/month; $0.008/credit PAYG
- [resend.com/docs/api-reference/emails/send-email](https://resend.com/docs/api-reference/emails/send-email) — Resend API reference
- [docs.firecrawl.dev/api-reference/endpoint/scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape) — Firecrawl scrape feature set (competitive baseline)

### Secondary (MEDIUM confidence)
- [brave.com/search/api](https://brave.com/search/api/) — $3-$5 CPM; free tier dropped Feb 12, 2026
- [serpapi.com/pricing](https://serpapi.com/pricing) — $75/month subscription, no PAYG; credits expire monthly
- [dev.to/ritza](https://dev.to/ritza/best-serp-api-comparison-2025-serpapi-vs-exa-vs-tavily-vs-scrapingdog-vs-scrapingbee-2jci) — Tavily vs Brave vs SerpAPI comparative analysis 2025
- Railway Playwright Docker patterns — `mcr.microsoft.com/playwright/python:*-jammy` base image approach, community documented

### Tertiary (LOW confidence)
- LibreOffice image size estimates (350-500MB) — based on community reports; actual size varies; validate during Phase 2
- faster-whisper real-time factor on Intel home server (2-4x for medium.en int8) — estimate from project README benchmarks; depends on home server CPU model

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*
