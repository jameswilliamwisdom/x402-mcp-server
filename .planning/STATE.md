---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Bismuth Launch
status: unknown
last_updated: "2026-03-16T07:29:40.269Z"
progress:
  total_phases: 11
  completed_phases: 11
  total_plans: 23
  completed_plans: 23
---

# State: Bismuth (x402 API Network)

**Milestone:** v2.0 — Bismuth Launch
**Last updated:** 2026-03-16
**Overall status:** Phase 11 complete — Bismuth live at https://usebismuth.com (pending: human nginx reload + Task 4 browser verify)

## Current Position

Phase: 11 of 16 (Rebrand + Domain + SSL) — COMPLETE
Plan: 11-02 complete (Tasks 2+3 executed; Task 4 human-verify checkpoint pending)
Status: 11-02 auto tasks done 2026-03-16; awaiting human browser verification
Last activity: 2026-03-16 — 11-02 cloudflared + deploy.sh + redeploy to usebismuth.com (2 tasks, 3 files, 44min)

Progress: [██████████] 100% (2/2 plans in Phase 11 complete)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-15)

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Phase 11 — Rebrand to Bismuth, register usebismuth.com, Cloudflare Tunnel HTTPS

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

### Pending Todos

- [Phase 11]: Run `sudo nginx -s reload` on home server (10.0.0.2) to activate absolute_redirect off fix — until then, URLs without trailing slashes (e.g. /pricing) return broken 301 redirects

### Blockers/Concerns

- [Phase 15]: crawlee[playwright]>=1.5.0 vs pinned playwright==1.44.0 — verify compatibility before writing crawl code
- [Phase 15]: SSRF validation must cover every discovered URL in the BFS loop, not just seed URL — pre-merge security gate
- [Phase 14]: Test with real Calibri + table DOCX on Railway before merge — font substitution may require Liberation fonts in Dockerfile
- [Phase 16]: Publish only after all backend phases deployed and integration-tested in both free and paid modes

## Session Continuity

Last session: 2026-03-16
Stopped at: 11-02 Task 4 human-verify checkpoint — usebismuth.com live, awaiting browser verification
Resume file: None
