# Phase 10: MCP Server Update + npm Publish - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Update `src/index.ts` with 5 new tool registrations (scrape, convert, search, email, transcribe) and 5 new APIS dict entries. Expand `x402_network_info` to cover all 8 APIs. Bump version to 1.1.0. Update README. Publish `x402-mcp-server@1.1.0` on npm.

</domain>

<decisions>
## Implementation Decisions

### Tool Naming & Descriptions
- Follow existing `x402_` prefix pattern in src/index.ts — Claude picks best verb_noun names based on existing conventions
- Claude decides whether to include pricing info in tool descriptions
- Claude decides which tools need limit/latency warnings in descriptions (transcription at minimum per roadmap)
- Review existing x402_send_email tool for consistency with the other 4 new tools — update if needed

### README & Documentation
- Claude decides tool listing format (flat table vs grouped by category) based on readability for 11 tools
- Claude decides whether to include usage examples
- Do not mention dotenvx in README — it's a personal workflow, not required for package users
- Claude decides whether to include a "What's New in 1.1.0" changelog section

### Health Check Design
- Claude decides health check approach (parallel vs sequential) for all 8 APIs
- Claude decides response format (status+URL+price vs status+URL only)
- Claude decides whether to distinguish home-server (transcription) from Railway APIs
- Claude decides failure reporting (show 'down' vs omit unreachable)

### Publishing Workflow
- Claude decides pre-publish verification approach (automated script vs manual walkthrough)
- Claude decides whether to update npm package.json metadata (description, keywords)
- Claude decides post-publish verification approach
- Git tag v1.1.0 after publish — matches v1.0 convention

### Claude's Discretion
- All tool naming decisions (verb_noun pattern following existing src/index.ts conventions)
- Tool description content (pricing, limits, latency warnings)
- README format and content depth
- Health check implementation (parallelism, format, failure handling)
- Pre/post-publish verification strategy
- npm metadata updates

</decisions>

<specifics>
## Specific Ideas

- Production URLs for APIS dict:
  - Scraping: https://x402-scraping-api-production.up.railway.app
  - Conversion: https://x402-conversion-api-production.up.railway.app
  - Search: https://x402-search-api-production.up.railway.app
  - Email: https://x402-email-api-production.up.railway.app
  - Transcription: https://transcribe.jameswisdom.ink
- x402_send_email already wired in during Phase 8 — review for consistency
- Each tool uses existing `apiGet`/`apiPost` helper pattern
- Zod validation on all user-facing params for all 5 new tools
- `npm pack --dry-run` to verify no secrets in published artifact
- All 11 tools must be callable in free mode before publish

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-mcp-server-update-npm-publish*
*Context gathered: 2026-03-15*
