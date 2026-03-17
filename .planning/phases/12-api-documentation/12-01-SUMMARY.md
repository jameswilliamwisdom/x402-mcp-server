---
phase: 12-api-documentation
plan: 01
subsystem: docs
tags: [astro, starlight, mdx, api-reference, x402]

# Dependency graph
requires:
  - phase: 11-rebrand-domain-ssl
    provides: Bismuth branding and usebismuth.com live site with Starlight docs
provides:
  - Web Scraping API reference page at /apis/scraping/
  - File Conversion API reference page at /apis/file-conversion/
  - Web Search API reference page at /apis/web-search/
  - 5-item APIs sidebar group in astro.config.mjs (all 5 API slugs registered)
  - Corrected pricing table in api-reference.mdx (conversion $0.02, web search $0.01, email $0.01)
affects: [12-api-documentation, deploy, api-reference]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MDX API reference page: frontmatter + Aside import + Endpoints (free above paid) + param table + curl + MCP tool call + Returns + Error codes"
    - "JSX-only comments in MDX files (HTML comments break MDX parser in this codebase)"
    - "SYNC price comments near hardcoded prices to prevent drift"
    - "Absolute paths with trailing slashes for all internal MDX links (nginx trailing slash requirement)"

key-files:
  created:
    - site/src/content/docs/apis/scraping.mdx
    - site/src/content/docs/apis/file-conversion.mdx
    - site/src/content/docs/apis/web-search.mdx
  modified:
    - site/astro.config.mjs
    - site/src/content/docs/api-reference.mdx

key-decisions:
  - "Slug naming uses singular API operation names: apis/scraping, apis/file-conversion, apis/web-search (not apis/web-scraping or apis/email-sending)"
  - "All 5 API sidebar slugs registered in Plan 12-01 even though email and audio-transcription pages are created in Plan 12-02 — Starlight silently omits missing slugs from sidebar, so pre-registration is safe"
  - "Pricing corrections committed in Task 1 alongside sidebar config (same logical change — fix incorrect API metadata)"

patterns-established:
  - "Per-page pattern: ## Endpoints (free first, paid second) -> Aside tip -> ## Parameters -> ## Example curl -> ## Example MCP Tool Call -> ## Returns -> ## Error Codes"
  - "Free test endpoint format: bold text with GET URL on same line, not a separate heading"
  - "HTTP 200 + success:false documented in both Returns Aside and after Error Codes table"

requirements-completed: [DOCS-01, DOCS-02, DOCS-03]

# Metrics
duration: 2min
completed: 2026-03-17
---

# Phase 12 Plan 01: API Documentation Summary

**Three Starlight MDX API reference pages (scraping, file-conversion, web-search) with parameter tables, curl examples, MCP tool calls, and error codes — plus sidebar registration for all 5 API pages and pricing corrections in api-reference.mdx**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-17T00:22:50Z
- **Completed:** 2026-03-17T00:25:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 modified, 3 created)

## Accomplishments

- Added 5-item "APIs" sidebar group in `astro.config.mjs` with slugs for all 5 v1.1 API pages (including email and audio-transcription stubs for Plan 12-02)
- Fixed three incorrect prices in `api-reference.mdx` pricing summary table: `x402_convert_file` $0.05 -> $0.02, `x402_web_search` $0.02 -> $0.01, `x402_send_email` $0.02 -> $0.01
- Created three complete API reference pages (`scraping.mdx`, `file-conversion.mdx`, `web-search.mdx`) — each with free-first endpoints, parameter table, curl examples, MCP tool call example, returns description, and error codes
- Astro build passes cleanly: 11 pages built with zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Update sidebar config and fix pricing table** - `ad728ba` (feat)
2. **Task 2: Write Web Scraping, File Conversion, and Web Search API reference pages** - `3e9fea9` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `site/astro.config.mjs` - Added APIs sidebar group with 5 slugs
- `site/src/content/docs/api-reference.mdx` - Fixed 3 incorrect prices, replaced placeholder with links to API pages
- `site/src/content/docs/apis/scraping.mdx` - Web Scraping API reference (DOCS-01, x402_scrape_url)
- `site/src/content/docs/apis/file-conversion.mdx` - File Conversion API reference (DOCS-02, x402_convert_file)
- `site/src/content/docs/apis/web-search.mdx` - Web Search API reference (DOCS-03, x402_web_search)

## Decisions Made

- Used singular operation slug names (`apis/scraping` not `apis/web-scraping`) — resolves the open question from RESEARCH.md
- All 5 API slugs pre-registered in sidebar even though Plan 12-02 creates the remaining 2 pages — Starlight handles missing pages gracefully (omits from rendered sidebar)
- Pricing corrections bundled with sidebar config in Task 1 rather than split across tasks — same logical concern (API metadata accuracy)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Build passed on first attempt. Pre-existing `email.mdx` and `audio-transcription.mdx` files were already present from Plan 12-02 (which had been executed prior to this plan run). These were not modified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 12-02 (Email Sending and Audio Transcription API pages) was already executed prior to this plan run — both pages exist and build successfully
- All 5 API pages render correctly under the "APIs" sidebar group
- Pricing table in api-reference.mdx is now accurate and consistent with backend source
- Phase 12 is effectively complete — both plans executed

## Self-Check: PASSED

All files confirmed present, all commits verified in git log.

---
*Phase: 12-api-documentation*
*Completed: 2026-03-17*
