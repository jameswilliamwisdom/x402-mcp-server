---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Universal Utility APIs
status: unknown
last_updated: "2026-03-15T17:52:22.678Z"
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 19
  completed_plans: 19
---

# State: x402 API Network — v1.1

**Milestone:** v1.1 — Universal Utility APIs
**Last updated:** 2026-03-15 (Phase 9 Plan 02)
**Overall status:** Phase 9 complete. x402-transcription-api deployed on home server — transcribe.jameswisdom.ink live via launchd + Cloudflare Tunnel. All 6 TRANS requirements satisfied end-to-end. Next: Phase 10 (MCP Server Update + npm Publish).

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 5 | Web Scraping API | Complete (2/2 plans) |
| 6 | File Conversion API | Complete (2/2 plans) |
| 7 | Web Search API | Complete (2/2 plans) |
| 8 | Email Sending API | Complete (2/2 plans) |
| 9 | Audio Transcription API | Complete (2/2 plans) |
| 10 | MCP Server Update + npm Publish | Pending |

## Completed

- [x] Milestone v1.0 shipped and archived (2026-03-12)
- [x] Milestone v1.1 goals gathered (2026-03-12)
- [x] v1.1 requirements defined — 29 requirements across 6 categories (2026-03-12)
- [x] Research completed — stack, features, architecture, pitfalls (2026-03-12)
- [x] v1.1 roadmap created — Phases 5-10, 100% requirement coverage (2026-03-12)
- [x] Phase 5 Plan 01: x402-scraping-api service built — 5 files, 604-line main.py (2026-03-12)
- [x] Phase 5 Plan 02: Docker validated, Railway deployed — https://x402-scraping-api-production.up.railway.app (2026-03-12)
- [x] Phase 6 Plan 01: x402-conversion-api service built — 5 files, 523-line main.py; CONV-01 through CONV-05 satisfied (2026-03-13)
- [x] Phase 6 Plan 02: Railway deployed — https://x402-conversion-api-production.up.railway.app; all endpoints verified in production (2026-03-13)
- [x] Phase 7 Plan 01: x402-search-api service built — 5 files, 266-line main.py; SEARCH-01 through SEARCH-05 satisfied (2026-03-14)
- [x] Phase 7 Plan 02: Railway deployed — https://x402-search-api-production.up.railway.app; all endpoints verified in production; Tavily key rotated, billing limit set (2026-03-14)
- [x] Phase 8 Plan 01: x402-email-api service built — 4 files, 313-line main.py; EMAIL-01 through EMAIL-05 satisfied (2026-03-14)
- [x] Phase 8 Plan 02: Railway deployed — https://x402-email-api-production.up.railway.app; all endpoints verified in production; x402_send_email tool wired into src/index.ts (2026-03-14)
- [x] Phase 9 Plan 01: x402-transcription-api service built — 3 files, 537-line main.py; TRANS-01 through TRANS-06 satisfied (2026-03-15)
- [x] Phase 9 Plan 02: x402-transcription-api deployed to home server — launchd plist + Cloudflare Tunnel; transcribe.jameswisdom.ink live (2026-03-15)

## Accumulated Decisions

- **Docker base image:** Use `mcr.microsoft.com/playwright/python:v1.44.0-jammy` for all Playwright Railway services — pre-bundled Chromium, no apt-get layer needed
- **SSRF middleware ordering:** Add SSRFMiddleware AFTER init_x402 — LIFO ensures SSRF runs before payment; confirmed pattern for all x402 + SSRF services
- **Context-level route handlers:** Register Playwright route handlers on `context` not `page` — context.close() clears accumulated Request/Response objects, prevents memory leak on long-running services
- **Shared time budget:** Use monotonic start + per-call `max(min_ms, remaining_budget_ms)` for Playwright sequences — independent per-action timeouts compound to 2x the intended ceiling
- **Discriminated union endpoint pattern:** Single POST /convert with Pydantic `Field(discriminator="type")` — one payment gate, one SSRF check, one test fixture for multi-operation APIs (Phase 6)
- **httpx redirect SSRF re-validation:** Use `event_hooks={"response": [on_redirect]}` to call `validate_url_for_ssrf(location)` on every redirect hop — prevents TOCTOU bypass after initial validation
- **WeasyPrint safe_url_fetcher:** Wrap `default_url_fetcher` with SSRF validation for all secondary resource fetches — required for CVE-2025-68616 mitigation
- **Docker WeasyPrint smoke test:** Add `RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"` after pip install — catches missing C libs at build time, not at first request
- **Per-wallet rate limit pattern:** Extract wallet from `decoded_payment["payload"]["authorization"]["from"]` after `@pay` runs; use `threading.Lock` for atomic check-and-increment; increment BEFORE upstream call to prevent quota manipulation via induced failures
- **Tavily search_depth:** Always use `"basic"` (1 credit); `include_answer` always `bool` not `"advanced"` string — prevents 2-credit overages making $0.01 endpoint unprofitable
- **request.state.x402_payer resolved:** Wallet is at `decoded_payment["payload"]["authorization"]["from"]` (not `x402_payer`) — confirmed via fastapi-x402 0.1.8 source inspection in Phase 7
- **Resend SDK is synchronous:** Use plain `def` route handler (not `async def`) — SDK uses `requests` internally; FastAPI auto-routes to thread pool preventing event-loop blocking
- **Per-domain rate limit added:** `check_and_increment_domain_limit` (5/wallet/domain/day) alongside wallet limit; both use single `_wallet_lock` to prevent deadlock
- **HTML body detection heuristic:** `startswith("<") and ("</" or "/>")` — conservative, omit "text" key for HTML bodies; Resend auto-generates plain-text server-side
- **ResendError mapping:** quota exhaustion → 503 (service-level, not caller fault); rate_limit → 503; auth errors → 500
- **x402-email-api production URL:** https://x402-email-api-production.up.railway.app — Railway project `exemplary-reflection`, root dir `x402-email-api/`
- **faster-whisper CPU config:** WhisperModel(small, cpu, int8, cpu_threads=4) — greedy decoding (beam_size=1, best_of=1, temperature=0) for predictable memory; cpu_threads must match physical cores (sysctl -n hw.physicalcpu)
- **PyAV for audio duration:** Use av.open(path).duration/1_000_000 (bundled with faster-whisper) — no system ffmpeg required; avoids launchd PATH pitfall
- **CTranslate2 thread safety:** threading.Lock serializes WhisperModel access; list(segments) MUST be called inside lock block to force lazy generator evaluation before lock release

## Open Questions

| Question | Blocking | Notes |
|----------|---------|-------|
| ~~Verified sender domain for Resend~~ | ~~Phase 8~~ | Resolved — domain jameswisdom.ink configured, FROM_ADDRESS hardcoded |
| ~~Public URL for home server transcription~~ | ~~Phase 9 + 10~~ | Resolved — transcribe.jameswisdom.ink live via Cloudflare Tunnel (2026-03-15) |
| ~~Docker build validation for Playwright image~~ | ~~Phase 5~~ | Resolved — pinned playwright==1.44.0, deployed successfully |
| ~~request.state.x402_payer attribute~~ | ~~Phase 5 Plan 02~~ | Resolved — wallet at decoded_payment["payload"]["authorization"]["from"] (Phase 7 Plan 01) |

## Notes

- 5 new APIs: web scraping, email sending, web search, file conversion, audio transcription
- 4 Railway services (scraping, search, email, file conversion) + 1 home server service (transcription)
- FastAPI + fastapi-x402 pattern for Railway services; hand-rolled x402 middleware for home server
- faster-whisper (NOT MLX Whisper) for transcription — home server is Intel x86_64
- Brand site / docs updates deferred to separate milestone
- Crypto sentiment stays as-is
- DOCX-to-PDF deferred to v1.2 (LibreOffice adds ~300MB Docker image)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-12)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** v1.1 — Universal Utility APIs

---

*State initialized: 2026-03-12*
*Last updated: 2026-03-15 — Phase 9 Plan 02 complete. x402-transcription-api deployed to home server; transcribe.jameswisdom.ink live via launchd + Cloudflare Tunnel. Phase 10 (MCP Server Update + npm Publish) is next.*
