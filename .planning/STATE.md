---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Bismuth Launch
status: unknown
last_updated: "2026-03-17T00:25:00Z"
progress:
  total_phases: 16
  completed_phases: 12
  total_plans: 25
  completed_plans: 25
---

# State: Bismuth (x402 API Network)

**Milestone:** v2.0 — Bismuth Launch
**Last updated:** 2026-03-17
**Overall status:** Phase 12 complete — API Documentation done. All 5 API reference pages live at usebismuth.com/apis/*. Phase 13 ready to begin.

## Current Position

Phase: 12 of 16 (API Documentation) — COMPLETE
Plan: 12-01 complete (sidebar config, pricing fix, 3 API pages), 12-02 complete (email + audio-transcription pages + deploy.sh smoke tests)
Status: Phase 12 fully complete — advancing to Phase 13
Last activity: 2026-03-17 — 12-02 complete: Email Sending + Audio Transcription API pages created; deploy.sh smoke tests added for all 5 API URLs; Astro build verified (11 pages)

Progress: [██████████] 100% (2/2 plans in Phase 12 complete)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-15)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Phase 13 — (next phase after API Documentation)

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

### Pending Todos

- [Phase 11]: Run `sudo nginx -s reload` on home server (10.0.0.2) to activate absolute_redirect off fix — until then, URLs without trailing slashes (e.g. /pricing) return broken 301 redirects

### Blockers/Concerns

- [Phase 15]: crawlee[playwright]>=1.5.0 vs pinned playwright==1.44.0 — verify compatibility before writing crawl code
- [Phase 15]: SSRF validation must cover every discovered URL in the BFS loop, not just seed URL — pre-merge security gate
- [Phase 14]: Test with real Calibri + table DOCX on Railway before merge — font substitution may require Liberation fonts in Dockerfile
- [Phase 16]: Publish only after all backend phases deployed and integration-tested in both free and paid modes

## Session Continuity

Last session: 2026-03-17
Stopped at: Completed 12-02-PLAN.md — Phase 12 API Documentation fully complete. All 5 API reference pages built and verified.
Resume file: None
