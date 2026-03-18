---
phase: 16-mcp-server-update-npm-publish
plan: 01
subsystem: api
tags: [mcp, x402, crawl, bismuth, npm, typescript]

# Dependency graph
requires:
  - phase: 15-shallow-site-crawl
    provides: POST /crawl and GET /crawl/test endpoints on scraping API
  - phase: 13-email-cc-bcc-attachments
    provides: cc/bcc/attachments backend support (MCP-02)
  - phase: 14-docx-to-pdf
    provides: docx conversion type backend support (MCP-03)
provides:
  - x402_crawl_site MCP tool registration using APIS.scraping.baseUrl
  - Version 2.0.0 in McpServer constructor and package.json
  - Updated README with 12 tools, What's New in 2.0.0, Bismuth branding
  - Updated package.json metadata (description, keywords)
affects: [16-02-PLAN (build and npm publish)]

# Tech tracking
tech-stack:
  added: []
  patterns: [conditional payload assembly for optional array params]

key-files:
  created: []
  modified: [src/index.ts, package.json, README.md]

key-decisions:
  - "x402_crawl_site placed after x402_transcribe_audio to maintain chronological addition order"
  - "Bismuth branding applied to H1 and tagline only — x402_ prefix, X402_PRIVATE_KEY, npx command unchanged"
  - "APIS.scraping description updated to mention crawl — no new APIS entry added"
  - "MCP-02 and MCP-03 verified present from prior phases — no code added for those"

patterns-established:
  - "Conditional payload assembly: always include params with .default() values, conditionally include truly optional arrays"

requirements-completed: [MCP-01, MCP-02, MCP-03, MCP-05]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 16 Plan 01: MCP Server Source Update Summary

**x402_crawl_site tool registered with $0.10 pricing via APIS.scraping.baseUrl, version bumped to 2.0.0, README updated with 12 tools and Bismuth branding**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T17:55:20Z
- **Completed:** 2026-03-18T17:57:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Registered x402_crawl_site as the 12th MCP tool, using APIS.scraping.baseUrl with paid ($0.10 POST /crawl) and free (GET /crawl/test) branches
- Verified MCP-02 (cc/bcc/attachments) and MCP-03 (docx enum) already present from Phases 13-14
- Bumped version to 2.0.0 in both McpServer constructor and package.json
- Updated README with 12-row tool table, What's New in 2.0.0 section, free mode crawl limitation, and Bismuth branding
- Updated package.json description and keywords (site-crawl, bismuth)
- TypeScript compiles cleanly with `npx tsc --noEmit`

## Task Commits

Each task was committed atomically:

1. **Task 1: Register x402_crawl_site, verify MCP-02/03, bump version, update APIS description and package.json** - `c73dcb3` (feat)
2. **Task 2: Update README with 12 tools, What's New in 2.0.0, and Bismuth branding** - `c5b52e6` (docs)

## Files Created/Modified
- `src/index.ts` - Added x402_crawl_site tool, updated APIS.scraping description, bumped McpServer version to 2.0.0
- `package.json` - Bumped version to 2.0.0, updated description, added site-crawl and bismuth keywords
- `README.md` - 12-tool table, What's New in 2.0.0, free mode crawl limitation, Bismuth branding in H1/tagline

## Decisions Made
- x402_crawl_site placed after x402_transcribe_audio in source to maintain chronological addition order
- Bismuth branding applied to H1 heading and tagline prose only — x402_ tool prefix, X402_PRIVATE_KEY env var, npx x402-mcp-server command, and "x402" mcpServers config key all unchanged per naming boundary constraints
- APIS.scraping description updated to "Scrape or crawl" — no new APIS dict entry created for crawl since it uses the same backend
- MCP-02 (cc/bcc/attachments) and MCP-03 (docx enum) verified as already present from prior phases — no code changes made

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- src/index.ts, package.json, and README.md are ready for `npm run build` and `npm publish` in Plan 16-02
- TypeScript compiles cleanly
- All 12 tools registered with correct pricing
- Version 2.0.0 set in both package.json and McpServer constructor

## Self-Check: PASSED

All files verified present, all commit hashes verified in git log.

---
*Phase: 16-mcp-server-update-npm-publish*
*Completed: 2026-03-18*
