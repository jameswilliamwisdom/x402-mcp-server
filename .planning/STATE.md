---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Bismuth Launch
status: unknown
last_updated: "2026-03-17T04:27:24.267Z"
progress:
  total_phases: 13
  completed_phases: 13
  total_plans: 27
  completed_plans: 27
---

# State: Bismuth (x402 API Network)

**Milestone:** v2.0 — Bismuth Launch
**Last updated:** 2026-03-17
**Overall status:** Phase 13 complete — 13-01 (backend CC/BCC/attachments) and 13-02 (MCP tool extension + docs) both done. All EMAIL-01 through EMAIL-04 requirements satisfied end-to-end.

## Current Position

Phase: 13 of 16 (Email Attachments + CC/BCC) — COMPLETE
Plan: 13-02 complete (MCP tool schema extension + email API docs update)
Status: Phase 13 complete — advancing to Phase 14
Last activity: 2026-03-17 — 13-02 complete: x402_send_email Zod schema extended with cc/bcc/attachments; conditional payload assembly; email API docs updated with parameter tables, attachment object schema, curl + MCP examples, rate limit and error code updates

Progress: [██████████] 100% (2/2 plans in Phase 13 complete)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-15)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Phase 14 — DOCX Conversion API

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

### Pending Todos

- [Phase 11]: Run `sudo nginx -s reload` on home server (10.0.0.2) to activate absolute_redirect off fix — until then, URLs without trailing slashes (e.g. /pricing) return broken 301 redirects

### Blockers/Concerns

- [Phase 15]: crawlee[playwright]>=1.5.0 vs pinned playwright==1.44.0 — verify compatibility before writing crawl code
- [Phase 15]: SSRF validation must cover every discovered URL in the BFS loop, not just seed URL — pre-merge security gate
- [Phase 14]: Test with real Calibri + table DOCX on Railway before merge — font substitution may require Liberation fonts in Dockerfile
- [Phase 16]: Publish only after all backend phases deployed and integration-tested in both free and paid modes

## Session Continuity

Last session: 2026-03-17
Stopped at: Completed 13-02-PLAN.md — Phase 13 complete. x402_send_email MCP tool extended with cc/bcc/attachments schema; email API docs updated with full parameter documentation, examples, and error codes.
Resume file: None
