# State: x402 API Network — v1.0

**Milestone:** v1.0 — npm Publish + Brand Site
**Last updated:** 2026-03-09
**Overall status:** Phase 1 complete — all 8 requirements (PKG-01..06, VAL-01..02) satisfied. Ready for Phase 2.

## Phase Status

| Phase | Name | Status | Blockers |
|-------|------|--------|----------|
| 1 | Package Hardening + Input Validation | Complete (2/2 plans) | None |
| 2 | npm Publish | Not started | Phase 1 ✓ |
| 3 | Brand Site Build | Not started | Phase 2 |
| 4 | Deployment | Not started | Phase 3 |

## Active Phase

Phase 2 — npm Publish. Phase 1 complete.

## Completed

- [x] Research completed (2026-03-09)
- [x] Requirements defined — 20 v1 requirements across 6 groups (2026-03-09)
- [x] Roadmap created — 4 phases, 100% requirement coverage (2026-03-09)
- [x] Phase 1 Plan 01: Package hardening — PKG-01..06 complete (2026-03-09)
- [x] Phase 1 Plan 02: Input validation — VAL-01..02 complete (2026-03-09)

## Open Questions

| Question | Blocking | Notes |
|----------|---------|-------|
| Home server domain / IP for brand site | Phase 3 (astro.config.mjs `site:` field), Phase 4 | Needed for correct canonical URLs and OG meta tags; can placeholder during Phase 3, must resolve before Phase 4 |
| npm account 2FA status | Phase 2 | Must be enabled before `npm publish`; cannot be verified programmatically |

## Known Risks

| Risk | Severity | Mitigation |
|------|---------|-----------|
| `.env` with `X402_PRIVATE_KEY` leaked to npm registry | CRITICAL | Phase 1 adds `files` whitelist before any publish attempt |
| Shebang stripped by `tsc` | HIGH | Phase 1 adds `postbuild` shebang injection script; verified with `head -1 dist/index.js` |
| `npx` without `-y` in docs breaks MCP stdio transport | HIGH | Phase 3 task: grep all site content before build |
| Astro SSR output mode breaks self-hosting | MEDIUM | Phase 3 explicitly sets `output: 'static'` in `astro.config.mjs` |
| `.planning/` exposed via nginx | LOW | Phase 4 verifies with `curl http://server/.planning/` — directory is not in `site/dist/` so risk is only nginx misconfiguration |

## Notes

- MCP server is already built and functional. All v1 work is packaging and documentation, not new features.
- `site/` subdirectory will have its own `package.json` — Astro is never in the npm bundle.
- Pricing sync between `src/index.ts` and brand site: use inline sync comments at v1; evaluate extracting shared `pricing.ts` constant when a third API is added or pricing changes.
- Package name on npm: `x402-mcp-server` (non-scoped). Users must use `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub) — this distinction should be called out in docs.

## Project Reference

See: `.planning/PROJECT.md` and `.planning/ROADMAP.md`

**Core value:** AI agents can discover and pay for useful APIs with zero integration friction
**Current focus:** Milestone v1.0 — Publish + Brand

---

*State initialized: 2026-03-09*
*Last updated: 2026-03-09 — Phase 1 Plan 02 complete: Zod regex on coin params (injection protection), .url() on url/pdf_url params (URL validation). Phase 1 fully complete. Deferred: pkg.main vs pkg.exports suggestion from publint (cosmetic, post-v1).*
