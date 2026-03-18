---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Bismuth Launch
status: unknown
last_updated: "2026-03-18T17:57:55Z"
progress:
  total_phases: 16
  completed_phases: 15
  total_plans: 32
  completed_plans: 31
---

# State: Bismuth (x402 API Network)

**Milestone:** v2.0 — Bismuth Launch
**Last updated:** 2026-03-18
**Overall status:** Phase 16 in progress — 16-01 (source code updates) complete. x402_crawl_site registered, version 2.0.0, README updated. 16-02 (build and npm publish) pending.

## Current Position

Phase: 16 of 16 (MCP Server Update + npm Publish) — IN PROGRESS
Plan: 16-01 complete, 16-02 pending (build and npm publish)
Status: 16-01 complete — source code ready for build and publish
Last activity: 2026-03-18 — 16-01 complete: x402_crawl_site tool registered with $0.10 pricing via APIS.scraping.baseUrl, version bumped to 2.0.0, README updated with 12 tools and Bismuth branding

Progress: [█████████░] 95% (1/2 plans in Phase 16 complete)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-15)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Phase 16-02 — Build and npm publish

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
- [Phase 16-01]: x402_crawl_site placed after x402_transcribe_audio — chronological addition order
- [Phase 16-01]: Bismuth branding applied to H1 and tagline only — x402_ prefix, X402_PRIVATE_KEY, npx command unchanged
- [Phase 16-01]: APIS.scraping description updated to "Scrape or crawl" — no new APIS dict entry for crawl
- [Phase 16-01]: MCP-02/03 verified present from prior phases — no code changes needed

### Pending Todos

- [Phase 11]: Run `sudo nginx -s reload` on home server (10.0.0.2) to activate absolute_redirect off fix — until then, URLs without trailing slashes (e.g. /pricing) return broken 301 redirects

### Blockers/Concerns

- [Phase 15]: RESOLVED — crawlee not needed; BFS uses stdlib (deque, fnmatch, posixpath) with existing playwright scrape_page()
- [Phase 15]: RESOLVED — SSRF validation implemented on every discovered URL before BFS enqueue (validate_url_for_ssrf(resolved))
- [Phase 14]: Test with real Calibri + table DOCX on Railway before merge — font substitution may require Liberation fonts in Dockerfile
- [Phase 16]: Publish only after all backend phases deployed and integration-tested in both free and paid modes

## Session Continuity

Last session: 2026-03-18
Stopped at: Completed 16-01-PLAN.md — x402_crawl_site tool registered, version 2.0.0, README updated with 12 tools and Bismuth branding. Ready for 16-02 (build and npm publish).
Resume file: None
