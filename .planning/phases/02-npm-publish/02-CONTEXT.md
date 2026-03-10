# Phase 2: npm Publish - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Update README with comprehensive install/config documentation and push repo to GitHub as a public repo. npm registry publish is deferred — using GitHub direct install (`npx -y github:jameswilliamwisdom/x402-mcp-server`) as the v1.0 distribution method.

</domain>

<decisions>
## Implementation Decisions

### Distribution Method
- GitHub direct install for v1.0 — no npm account needed
- Install command: `npx -y github:jameswilliamwisdom/x402-mcp-server`
- npm registry publish deferred until account issues resolved
- GitHub repo: public, under `jameswilliamwisdom` username

### README Content
- Comprehensive — all 6 tools with descriptions + pricing, quick start (free + paid), config JSON, env var setup, links to brand site
- Developer-focused tone — straight to the point, no marketing fluff
- Include badges: npm version (when published), license, Node version
- This is the npm registry page AND the GitHub landing page

### MCP Client Configs
- Include configs for ALL major clients: Claude Desktop, Claude Code, Cursor, Windsurf
- All configs use `npx -y github:jameswilliamwisdom/x402-mcp-server`
- Env var (X402_PRIVATE_KEY) referenced via .env file, not inline in config JSON
- Free mode config shown separately (no env var needed)

### Claude's Discretion
- README section ordering
- Badge selection and styling
- Exact formatting of tool/pricing table
- How to structure the free vs paid mode sections

</decisions>

<specifics>
## Specific Ideas

- GitHub username: `jameswilliamwisdom`
- Repo name: `x402-mcp-server`
- Show free mode first (no wallet needed) — lower barrier to entry
- Reference brand site docs for wallet setup guide (will exist after Phase 3)

</specifics>

<deferred>
## Deferred Ideas

- npm registry publish — deferred until npm account issues resolved. When ready: `npm publish --access public`, update README install commands to use package name instead of GitHub URL
- npm badges won't work until published — use shield.io GitHub badges instead for v1.0
- Git tag `v1.0.0` — defer until npm publish happens

</deferred>

---

*Phase: 02-npm-publish*
*Context gathered: 2026-03-10*
