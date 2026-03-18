---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Bismuth Launch
status: unknown
last_updated: "2026-03-18T17:20:46.352Z"
progress:
  total_phases: 15
  completed_phases: 15
  total_plans: 30
  completed_plans: 30
---

# State: Bismuth (x402 API Network)

**Milestone:** v2.0 — Bismuth Launch
**Last updated:** 2026-03-18
**Overall status:** Phase 15 complete — 15-01 (shallow BFS crawl endpoint) done. CRAWL-01 through CRAWL-08 requirements satisfied.

## Current Position

Phase: 15 of 16 (Shallow Site Crawl) — COMPLETE
Plan: 15-01 complete (BFS crawl endpoint with SSRF-gated link discovery, path filters, partial results)
Status: Phase 15 complete — advancing to Phase 16
Last activity: 2026-03-18 — 15-01 complete: POST /crawl with BFS up to 15 pages, SSRF on every discovered URL, same-origin enforcement, include/exclude path filters, partial result accumulation, GET /crawl/test fixture endpoint

Progress: [██████████] 100% (1/1 plans in Phase 15 complete)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-15)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Phase 16 — MCP Publish

## Accumulated Context

### Decisions

Full decision log in PROJECT.md Key Decisions table. Recent decisions for v2.0:

- mammoth + WeasyPrint for DOCX (not LibreOffice) — zero Docker size cost, semantic fidelity
- crawlee[playwright] for crawl — must verify vs pinned playwright==1.44.0 before Phase 15
- Sync crawl with 15-page cap — async job pattern deferred to v2.x
- Email before DOCX before Crawl — ascending complexity order, validates redeploy cycle
- MCP publish last — must follow all backend deployments and integration tests
- [Phase 11]: MCP tool names (x402_*), package name, and env var kept as-is — only brand copy changes to Bismuth
- [Phase 11]: pricing.astro fixed as auto-fix deviation — stray x402 Network and x402.todo references cleaned up even though file was not in plan file list
- [Phase 11]: cloudflared runs on home server (10.0.0.2) — ingress rule uses localhost:8888 (nginx), not 10.0.0.72:8888 (Mac)
- [Phase 11]: nginx absolute_redirect off + try_files fix on disk at home server, requires sudo nginx -s reload to activate
- [Phase 11-rebrand-domain-ssl]: Bismuth site verified publicly at https://usebismuth.com — padlock present, no SSL warnings, Bismuth branding confirmed by user on 2026-03-16
- [Phase 12-01]: Slug naming convention for API pages: singular operation names — apis/scraping, apis/file-conversion, apis/web-search (not apis/web-scraping or apis/email-sending)
- [Phase 12-01]: All 5 API sidebar slugs pre-registered in 12-01 even though email/audio-transcription pages created in 12-02 — Starlight handles missing slugs gracefully
- [Phase 12-01]: Pricing corrections (x402_convert_file $0.02, x402_web_search $0.01, x402_send_email $0.01) bundled with sidebar config in Task 1
- [Phase 12-02]: Email fixed From address documented in note Aside (not caution) — expected API behavior, not a warning
- [Phase 12-02]: Transcription branching response documented as two separate JSON code blocks — clearer than table for showing full schema variants
- [Phase 12-02]: Billing-on-download caveat in caution Aside immediately after hard limits explanation for maximum visibility
- [Phase 13-01]: Attachment size check uses decoded byte length (len(base64.b64decode(v))), NOT string length — base64 33% expansion means string length check would reject 18.7MB files
- [Phase 13-01]: base64 string passed directly to Resend SDK content field — Resend accepts Union[List[int], str] not bytes; Python bytes would raise TypeError during JSON serialization
- [Phase 13-01]: List[EmailStr] for cc/bcc — email-validator rejects CRLF injection automatically; List[str] would not
- [Phase 13-01]: domain rate limiter extended to all_recipients loop — prevents CC/BCC domain bypass attack vector
- [Phase 13-01]: path field omitted from AttachmentItem — SSRF risk, explicitly Out of Scope per REQUIREMENTS.md
- [Phase 13-02]: All new Zod fields use .optional() — backward compat for existing callers passing only to/subject/body
- [Phase 13-02]: Payload assembly uses conditional includes matching reply_to pattern — backend rejects null values
- [Phase 14]: Lazy import mammoth inside sync_docx_to_pdf (matches plan pattern, avoids top-level import for optional dependency)
- [Phase 14]: No base_url passed to WeasyPrint for DOCX — mammoth produces self-contained HTML with data URI images
- [Phase 14]: No handler changes needed for docx — existing payload assembly passes type and url generically
- [Phase 14]: CONV-03 fidelity note placed as caution Aside between Returns bullets and CSV note for maximum visibility
- [Phase 15]: No new runtime dependencies for crawl -- BFS uses stdlib deque, fnmatch, posixpath (crawlee not needed)
- [Phase 15]: seed_netloc derived from final_url not input URL -- handles redirect-based domain changes correctly
- [Phase 15]: wait_for=None for all crawl pages -- crawl prioritizes breadth over precision
- [Phase 15]: SSRF validation on every discovered URL before BFS enqueue, not just seed URL
- [Phase 15]: Partial results returned on per-page failure; only browser 503 aborts entire crawl
- [Phase 15]: GET /crawl/test registered before POST /crawl to avoid FastAPI path parameter collision

### Pending Todos

- [Phase 11]: Run `sudo nginx -s reload` on home server (10.0.0.2) to activate absolute_redirect off fix — until then, URLs without trailing slashes (e.g. /pricing) return broken 301 redirects

### Blockers/Concerns

- [Phase 15]: RESOLVED — crawlee not needed; BFS uses stdlib (deque, fnmatch, posixpath) with existing playwright scrape_page()
- [Phase 15]: RESOLVED — SSRF validation implemented on every discovered URL before BFS enqueue (validate_url_for_ssrf(resolved))
- [Phase 14]: Test with real Calibri + table DOCX on Railway before merge — font substitution may require Liberation fonts in Dockerfile
- [Phase 16]: Publish only after all backend phases deployed and integration-tested in both free and paid modes

## Session Continuity

Last session: 2026-03-18
Stopped at: Completed 15-01-PLAN.md — Phase 15 complete. POST /crawl with BFS up to 15 pages, SSRF-gated link discovery, same-origin enforcement, include/exclude path filters, partial result accumulation. GET /crawl/test fixture endpoint. Dockerfile updated.
Resume file: None
