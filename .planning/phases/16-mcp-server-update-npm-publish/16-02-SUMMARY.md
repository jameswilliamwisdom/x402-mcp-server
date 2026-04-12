---
phase: 16-mcp-server-update-npm-publish
plan: 02
status: complete
completed: "2026-04-06"
one_liner: "Published x402-mcp-server@2.0.0 to npm with 12 tools, all pre-publish checks passed, git tag v2.0.0 pushed"
---

# Summary: 16-02 Build + Pre-Publish Gate + npm Publish

## What Was Built

Published x402-mcp-server@2.0.0 to npm registry with all 12 MCP tools and Bismuth branding.

## Tasks Completed

1. **Pre-publish checklist** — All 10 gates passed:
   - Phase 15 crawl backend smoke test (GET /crawl/test returns fixture data)
   - TypeScript compiles cleanly, 12 tools confirmed
   - Shebang present on dist/index.js, stripped from dist/index.d.ts (postbuild script fixed)
   - Tarball has exactly 5 files (no secrets)
   - npm auth confirmed as jameswilliamwisdom
   - Version 2.0.0 consistent across package.json and src/index.ts

2. **npm publish** — Human passkey auth, package live on registry

3. **Post-publish verification** — `npm view x402-mcp-server@2.0.0` confirms 2.0.0 live

4. **Git tag** — `v2.0.0` annotated tag created and pushed to origin

## Deviation

- **Crawl backend not yet deployed to Railway** at plan execution time — was deployed as part of pre-publish checks (deviation from assumption that Phase 15 had already deployed). Resolved by deploying during Task 1.
- **dist/index.d.ts had shebang leak** — postbuild script was already handling this but the `.d.ts` shebang strip was verified and confirmed working.

## Post-Publish Addition (same session)

After npm publish, a test suite was added:
- Vitest framework with 35 tests (helpers + all 12 tools via MCP InMemoryTransport)
- Extracted `src/helpers.ts` for testability
- Guarded `main()` auto-connect for test imports
- Committed as separate commit (`test: add vitest suite...`)
- Tests are NOT in the npm tarball (correct — `files` whitelist excludes `src/`)

## Self-Check: PASSED

- FOUND: `npm view x402-mcp-server@2.0.0` returns version 2.0.0
- FOUND: `git tag v2.0.0` exists
- FOUND: 35 tests passing in `src/__tests__/`
- FOUND: commit `4412254` (test suite)

---
*Phase: 16-mcp-server-update-npm-publish*
*Completed: 2026-04-06*
