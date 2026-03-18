# Phase 16: MCP Server Update + npm Publish - Research

**Researched:** 2026-03-18
**Domain:** TypeScript MCP server tool registration, npm publish workflow
**Confidence:** HIGH — all findings derived from direct source inspection of src/index.ts, package.json, README.md, x402-scraping-api/main.py, and confirmed Phase 10/13/14 precedent commits
**Method:** MECE decomposition (2 dimensions: INTEGRATION, PITFALLS)

---

## Summary

Phase 16 has exactly one net-new code change and one publish operation. The only code that must be written is registering `x402_crawl_site` in `src/index.ts` — a new MCP tool wrapping the `POST /crawl` endpoint already deployed on the scraping Railway service. Requirements MCP-02 and MCP-03 are already satisfied: the `x402_send_email` Zod schema was extended with cc/bcc/attachments in Phase 13 (commit `ee3bf95`) and the `x402_convert_file` type enum was extended with `"docx"` in Phase 14 (commit `d5d5d9e`). The planner must verify these are present but should not create tasks to add them again.

The remaining work is mechanical: bump the version string to `2.0.0` in both `package.json` and the `McpServer` constructor in `src/index.ts`, update `package.json` description and keywords to mention crawl, update the README to add the crawl tool row and update stale descriptions, then follow the exact npm publish pipeline used for v1.1.0 in Phase 10.

The publish step is non-autonomous — npm 2FA via passkey (iCloud Keychain) may require interactive browser action. A mandatory pre-publish gate is the smoke test of the Railway crawl endpoint to confirm Phase 15's backend is live before committing to a publish.

**Primary recommendation:** Register x402_crawl_site using APIS.scraping.baseUrl (no new APIS entry), verify MCP-02/MCP-03 are already done, bump to 2.0.0, update README, publish via the Phase 10 pipeline with the mandatory pre-publish checklist.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | x402_crawl_site tool registered in src/index.ts with Zod schema | Full Zod schema and handler provided verbatim (INTEGRATION). Placement: after x402_transcribe_audio, before `// ─── Start ───` section. Uses APIS.scraping.baseUrl, POST /crawl ($0.10), GET /crawl/test (free). |
| MCP-02 | x402_send_email Zod schema updated to accept cc, bcc, attachments | Already complete in src/index.ts lines 502–511 (Phase 13, commit ee3bf95). Planner task: verify-only, not add. (INTEGRATION + PITFALLS) |
| MCP-03 | x402_convert_file Zod schema updated to accept type: "docx" | Already complete in src/index.ts line 609 (Phase 14, commit d5d5d9e). Planner task: verify-only, not add. (INTEGRATION + PITFALLS) |
| MCP-04 | Package version bumped to 2.0.0, published to npm | Version bump: package.json + src/index.ts constructor (both must be updated atomically). Full 9-step publish pipeline with pre-publish checklist. (INTEGRATION + PITFALLS) |
| MCP-05 | README updated with all 12 tools and Bismuth branding | Add crawl row, update convert/email descriptions, add free-mode bullet, replace "What's New in 1.1.0" with "What's New in 2.0.0", update H1/brand prose to Bismuth while keeping x402 in npm commands. (INTEGRATION + PITFALLS) |

---

## Standard Stack

**Language and runtime:** TypeScript, compiled to ESM via `tsc`, `"type": "module"` in package.json. Output: `dist/index.js` (with shebang injected by postbuild script) + `dist/index.d.ts`.

**Core dependencies (unchanged — no additions needed):**
```json
{
  "@modelcontextprotocol/sdk": "^1.11.0",
  "viem": "^2.0.0",
  "x402-fetch": "^1.1.0",
  "zod": "^4.3.6"
}
```

No new dependencies are introduced in Phase 16. `x402_crawl_site` reuses existing helpers (`apiPost`, `apiGet`, `textResult`, `errorResult`) and the existing `APIS.scraping.baseUrl`.

**Build pipeline:**
- `npm run build` → `tsc` → `postbuild` shebang injection
- `prepublishOnly` script in package.json auto-runs build before publish
- `"files": ["dist", "README.md", "LICENSE"]` — tarball whitelist (5 files, unchanged)

**npm auth:** `jameswilliamwisdom` (passkey via iCloud Keychain, verified 2026-03-18). Session may expire — always run `npm whoami` immediately before `npm publish`.

---

## Architecture Patterns

### Tool Registration Pattern

Every tool follows the same four-part call to `server.tool()`:

```typescript
server.tool(
  "tool_name",           // 1. string: MCP tool name (x402_ prefix)
  `description text`,    // 2. string: multi-line with Price/mode info
  {                      // 3. object: Zod input schema
    param: z.string().describe("..."),
  },
  async (params) => {    // 4. handler: receives typed params
    const base = APIS.<key>.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = { /* required fields */ };
        // optional fields: if (params.x) payload.x = params.x;
        const data = await apiPost(base, "/endpoint", payload, true);
        return textResult({ mode: "paid", cost: "$X.XX", ...data });
      } else {
        const data = await apiGet(base, "/endpoint/test");
        return textResult({ mode: "free_test", note: "...", ...data });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

**Invariants observed in all 11 existing tools:**
- Always use `const base = APIS.<key>.baseUrl` — never hardcode URLs in handlers
- Payment gate: `const usePaid = !!PRIVATE_KEY`
- Paid branch: `apiPost(..., true)` or `apiGet(..., true)` (fourth arg enables payment)
- Free branch: `apiGet(base, "/endpoint/test")` with no payment arg
- Entire body wrapped in `try/catch (err: any) { return errorResult(err.message); }`
- Optional params use conditional assembly: `if (params.x !== undefined) payload.x = params.x`

### Crawl Shares the Scraping APIS Entry

`x402_crawl_site` does NOT get its own APIS dict entry. Both `POST /crawl` and `POST /scrape` live on the same Railway service (`https://x402-scraping-api-production.up.railway.app`). The handler uses `APIS.scraping.baseUrl` directly. Adding a new `crawl:` entry would cause `x402_network_info` (which enumerates `Object.entries(APIS)`) to show a duplicate health check for the same service.

Update `APIS.scraping.description` to mention crawl: `"Scrape or crawl any URL and return structured JSON: markdown, links, tables, images, metadata"`.

### Optional Fields — Conditional Payload Assembly

Optional params are not spread or ternary-inlined. The pattern is:
```typescript
if (params.include_paths) payload.include_paths = params.include_paths;
if (params.exclude_paths) payload.exclude_paths = params.exclude_paths;
```
Fields with `.default()` (`max_pages`, `max_depth`) are always defined when the handler runs — include them unconditionally in the paid payload. Only truly optional fields (`include_paths`, `exclude_paths`) use conditional assembly.

### Tool Placement Convention

Tools are registered in a flat sequence, each preceded by an ASCII banner comment. `x402_crawl_site` is placed after `x402_transcribe_audio` and before the `// ─── Start ───` section:
```typescript
// ─── Tool: x402_crawl_site ──────────────────────────────────────────────────
```

### Version Bump — Atomic Two-File Update

Version must be updated in both locations atomically in the same commit:
1. `package.json` `"version"` field
2. `src/index.ts` `new McpServer({ version: ... })` constructor (line 188)

TypeScript compilation and `npm publish` do NOT catch mismatches between these two string literals.

### Two-Commit Publish Workflow

Phase 10 established this sequence (must be followed exactly):
1. Source commit: `git commit -m "feat(16-01): register x402_crawl_site, bump to v2.0.0"`
2. Build + dist commit: `git commit -m "build(16-02): compile v2.0.0 dist"`
3. `npm publish`
4. Tag commit: `git tag v2.0.0 && git push origin v2.0.0`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pre-publish tarball verification | Custom file listing script | `npm pack --dry-run` | Shows exactly what npm will publish — ground truth |
| npm auth check | Manual token inspection | `npm whoami` | One command, definitive answer |
| Version management | Manual string edits without verification | Update both `package.json` and `src/index.ts` McpServer constructor explicitly and verify with grep | `npm version` creates git tags automatically, conflicting with this project's manual tagging workflow |
| Post-publish verification | Browser check | `npm view x402-mcp-server@2.0.0` | CLI-verifiable, returns JSON |
| Secret scanning before publish | Custom grep | `npm pack --dry-run` + inspect the 5 listed files | The tarball contents list IS the truth |
| Crawl test endpoint verification | Full paid crawl test | `curl https://x402-scraping-api-production.up.railway.app/crawl/test` | Free, no USDC needed, verifies Phase 15 backend is live |
| Adding MCP-02/03 code | Writing cc/bcc/attachments or docx into src/index.ts | Read current src/index.ts first — both are already implemented | Creating duplicate code or corrupting existing enums |

**Key:** Do NOT use `npm version 2.0.0` — it auto-creates a git tag before publish, conflicting with the manual tagging workflow established in Phase 10.

---

## Common Pitfalls

### Version Bump Is Three Places, Not Two

- `package.json` → `"version": "2.0.0"`
- `src/index.ts` McpServer constructor (line 188) → `version: "2.0.0"`
- `package.json` `description` field → add "shallow site crawl" to capability list
- `package.json` `keywords` → add `"site-crawl"` (and optionally `"bismuth"`)

Verify: `grep '"version"' package.json` and `grep 'version:' src/index.ts | grep -v "//"` must both show `2.0.0`.

### MCP-02 and MCP-03 Are Already Done — Do Not Re-Implement

`x402_send_email` Zod schema already has `cc`, `bcc`, `attachments` (Phase 13, lines 502–511). `x402_convert_file` type enum already has `"docx"` (Phase 14, line 609). Tasks for these requirements must be verify-only. Creating add tasks will produce redundant edits that risk corrupting existing code.

Verify MCP-02: `grep -A 5 "cc:" src/index.ts | head -10` — must show `z.array(z.string().email()).optional()`
Verify MCP-03: `grep 'enum.*docx' src/index.ts` — must show `z.enum(["image", "csv", "html_pdf", "docx"])`

### Crawl Price Is $0.10, Not $0.02

`POST /crawl` has `@pay("$0.10")` (x402-scraping-api/main.py line 829). `POST /scrape` has `@pay("$0.02")` (line 707). Copying the `x402_scrape_url` handler verbatim would embed `cost: "$0.02"` — wrong. The crawl tool description must say `$0.10 USDC per crawl` and `textResult` must include `cost: "$0.10"`.

### max_pages / max_depth Must Be Numbers in the Payload, Not Strings

`apiPost` serializes via `JSON.stringify` — numbers are preserved as-is. Do NOT use `String(params.max_pages)` (that pattern only applies to the screenshot tool which uses URLSearchParams/GET). The Python backend has `max_pages: int = Field(...)` — a string value causes a 422.

### npm Publish Is Irreversible — Mandatory Pre-Publish Checklist

```bash
# 1. Smoke test Phase 15 crawl backend
curl -s https://x402-scraping-api-production.up.railway.app/crawl/test | python3 -m json.tool | head -20
# Expect: crawl fixture JSON, not 404 or 502

# 2. Build fresh
npm run build

# 3. Verify shebang on compiled output
head -1 dist/index.js   # Must be: #!/usr/bin/env node
head -1 dist/index.d.ts  # Must NOT be #!/usr/bin/env node

# 4. Verify artifact starts clean
timeout 5 node dist/index.js 2>&1 || true
# No "Fatal:" output = pass

# 5. Verify tarball contents
npm pack --dry-run
# Expect exactly 5 files: dist/index.js, dist/index.d.ts, README.md, LICENSE, package.json

# 6. Verify tool count
grep -c "server.tool(" src/index.ts
# Must be: 12

# 7. Verify version consistency
grep '"2.0.0"' package.json src/index.ts
# Must return two matches

# 8. Verify npm auth
npm whoami  # Must be: jameswilliamwisdom

# 9. Publish (non-autonomous — passkey/OTP may require interactive input)
npm publish

# 10. Verify publish
npm view x402-mcp-server@2.0.0

# 11. Tag
git tag v2.0.0
git push origin v2.0.0
```

### npm 2FA — Publish Step Is Non-Autonomous

npm uses passkey auth (iCloud Keychain + `--auth-type=web`). If `npm publish` hangs or outputs "Enter OTP", the user must respond interactively. Mark the publish task as `autonomous: false`.

### README Bismuth Branding Boundary

**What changes to Bismuth:** H1 heading, prose references to "x402 API Network", marketing copy, "What's New" section.

**What must NOT change:** `x402-mcp-server` npm package name in install commands, `x402_*` tool name prefix in examples, `X402_PRIVATE_KEY` env var, `"x402"` mcpServers config key in Quick Start JSON blocks, `npx x402-mcp-server` command. Changing any of these would publish broken documentation — `bismuth-mcp-server` does not exist on npm.

### README Tool Count Must Be Exactly 12

Currently 11 rows in the tool table. After Phase 16, exactly 12. Two existing descriptions are also stale:
- `x402_convert_file` → add "DOCX to PDF" to description
- `x402_send_email` → mention CC/BCC and attachments
- Free mode limitations list → add crawl bullet: `"Site crawling returns fixture data (no live crawl)"`
- "What's New in 1.1.0" → replace with "What's New in 2.0.0"

### Stale dist/ Risk

`prepublishOnly` re-runs `tsc` automatically, but only if there are no silently-ignored TypeScript errors. Run `npx tsc --noEmit` before build to surface any type errors. After build, verify `dist/index.js` starts clean with `timeout 5 node dist/index.js`.

### Do Not Alter `files` Whitelist

`package.json` `files: ["dist", "README.md", "LICENSE"]` is correct and must not be changed. Adding `"src"` or any `"x402-*-api"` directory would publish the Python backend source and planning files. Phase 16 requires no change to this array.

---

## Code Examples

### Complete x402_crawl_site Registration (Drop-In Ready)

```typescript
// ─── Tool: x402_crawl_site ──────────────────────────────────────────────────

server.tool(
  "x402_crawl_site",
  `Crawl a website via BFS and return per-page extraction results (markdown, links, tables, images, metadata).
Price: $0.10 USDC per crawl (paid mode) | Free test: returns fixture data.

Crawls up to max_pages pages starting from the seed URL, up to max_depth link hops deep.
Same extraction pipeline as x402_scrape_url — each page returns markdown, links, tables, images, metadata.
Optional include_paths/exclude_paths glob filters (e.g. '/blog/*') restrict which URLs are followed.
Hard limits: max 15 pages, max depth 5. Response includes pages_requested, pages_crawled, pages_skipped.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: seed_url, pages_requested, pages_crawled, pages_skipped, reasons_skipped, results array.`,
  {
    url: z.string().url()
      .describe("Seed URL to begin crawling (http/https, max 2048 chars)"),
    max_pages: z.number().int().min(1).max(15).default(10)
      .describe("Maximum pages to crawl (1-15, default: 10)"),
    max_depth: z.number().int().min(1).max(5).default(2)
      .describe("Maximum link depth from seed URL (1-5, default: 2)"),
    include_paths: z.array(z.string()).max(20).optional()
      .describe("Only follow URLs matching these path glob patterns (e.g. '/blog/*', max 20)"),
    exclude_paths: z.array(z.string()).max(20).optional()
      .describe("Skip URLs matching these path glob patterns (e.g. '/admin/*', max 20)"),
  },
  async (params) => {
    const base = APIS.scraping.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = {
          url: params.url,
          max_pages: params.max_pages,
          max_depth: params.max_depth,
        };
        if (params.include_paths) payload.include_paths = params.include_paths;
        if (params.exclude_paths) payload.exclude_paths = params.exclude_paths;
        const data = await apiPost(base, "/crawl", payload, true);
        return textResult({ mode: "paid", cost: "$0.10", ...data });
      } else {
        const data = await apiGet(base, "/crawl/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live crawling.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

### APIS.scraping Description Update

```typescript
// Before:
description: "Scrape any URL and return structured JSON: markdown, links, tables, images, metadata",
// After:
description: "Scrape or crawl any URL and return structured JSON: markdown, links, tables, images, metadata",
```

### package.json Version and Metadata Updates

```json
{
  "version": "2.0.0",
  "description": "MCP server for the x402 API Network — screenshot, PDF, crypto sentiment, web scraping, shallow site crawl, file conversion, web search, email, and audio transcription tools with USDC micropayments on Base",
  "keywords": ["mcp", "x402", "usdc", "base", "micropayments", "ai-agent", "screenshot", "pdf", "crypto-sentiment", "web-scraping", "site-crawl", "email", "web-search", "file-conversion", "transcription", "bismuth"]
}
```

### McpServer Constructor Version Update (src/index.ts line 188)

```typescript
const server = new McpServer({
  name: "x402-api-network",
  version: "2.0.0",
});
```

### README Tool Table — New Row to Add

```markdown
| `x402_crawl_site` | Crawl a website via BFS and return per-page markdown, links, tables, images, metadata | $0.10 / crawl |
```

### README "What's New in 2.0.0" Section

```markdown
## What's New in 2.0.0

Three capability extensions and one new tool:
- **Shallow Site Crawl** — new x402_crawl_site tool: BFS crawl up to 15 pages from a seed URL
- **Email CC/BCC/Attachments** — x402_send_email now accepts cc, bcc, and base64 file attachments
- **DOCX to PDF** — x402_convert_file now supports type: "docx" for DOCX document conversion
```

### Verification Commands

```bash
# TypeScript type-check (before build)
cd /Users/jameswisdom/projects/x402-mcp-server && npx tsc --noEmit

# Tool count
grep -c "server.tool(" src/index.ts  # Expected: 12

# Version consistency
grep '"2.0.0"' src/index.ts package.json  # Expected: 2 matches

# Email schema (MCP-02 verify)
grep -A 5 "cc:" src/index.ts | head -10  # Must show z.array(z.string().email()).optional()

# Convert file schema (MCP-03 verify)
grep 'enum.*docx' src/index.ts  # Must show z.enum(["image", "csv", "html_pdf", "docx"])

# Crawl backend smoke test
curl -s https://x402-scraping-api-production.up.railway.app/crawl/test | python3 -m json.tool | head -20
```

---

## State of the Art

The x402 MCP server follows the Model Context Protocol SDK v1.11.0 `server.tool()` API. The Zod v4 schema approach (each field is a `z.*` validator, no intermediate schema variable) is correct for this SDK version and matches all 11 existing tools.

The crawl tool is the 9th distinct API capability wrapped by this server. The pattern of sharing a baseUrl between related tools (`x402_sentiment`, `x402_market_overview`, and `x402_intelligence` all share `APIS.sentiment.baseUrl`) is already established — `x402_crawl_site` sharing `APIS.scraping.baseUrl` with `x402_scrape_url` follows the same precedent.

Semver 2.0.0 is a milestone brand signal (the Bismuth v2.0 launch), not a technical breaking-change signal. All schema additions use `.optional()` or have `.default()` values, so existing callers are not broken. Users with `^1.x.x` pinning will not auto-upgrade — they must opt in.

---

## Open Questions

None. Both dimensions agree on all findings. MCP-02 and MCP-03 pre-completion is confirmed by direct source inspection of `src/index.ts` and cross-referenced against Phase 13/14 summary commits. The crawl backend live state should be confirmed by smoke test at plan execution time (not a research gap — a runtime gate).

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | Both dimensions agree on all findings. INTEGRATION provides implementation detail; PITFALLS provides risk/verification guidance. No conflicts. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples, Phase Requirements. |
| Dimension Coverage | PASS | INTEGRATION findings integrated: tool registration pattern, APIS dict, MCP-01 schema, MCP-02/03 pre-completion status, MCP-04 publish pipeline, MCP-05 README changes. PITFALLS findings integrated: 15 pitfalls across version drift, pre-publish checklist, branding boundary, auth state, tool count, tarball safety. |
| Requirement Coverage | PASS | MCP-01 → crawl tool Zod schema + handler (INTEGRATION); MCP-02 → verify-only, already complete (INTEGRATION + PITFALLS); MCP-03 → verify-only, already complete (INTEGRATION + PITFALLS); MCP-04 → version bump + publish pipeline (both dimensions); MCP-05 → README changes enumerated (both dimensions). |

---

## Sources

### Primary (HIGH confidence)
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — 11 registered tools, version "1.1.0" in McpServer constructor, email/convert schemas already updated, APIS dict, all helper functions
- `/Users/jameswisdom/projects/x402-mcp-server/package.json` — version "1.1.0", files whitelist `["dist", "README.md", "LICENSE"]`, scripts, dependencies, keywords, description
- `/Users/jameswisdom/projects/x402-mcp-server/README.md` — 11-tool table, "What's New in 1.1.0", stale convert/email descriptions, free mode limitation bullets
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — `@pay("$0.02")` for POST /scrape (line 707), `@pay("$0.10")` for POST /crawl (line 829), GET /crawl/test fixture endpoint (line 821), CrawlRequest Pydantic schema
- `.planning/phases/13-email-attachments-cc-bcc/13-02-SUMMARY.md` — confirms cc/bcc/attachments Zod schema merged in commit `ee3bf95`
- `.planning/phases/14-docx-to-pdf-conversion/14-02-SUMMARY.md` — confirms `"docx"` enum merged in commit `d5d5d9e`
- `.planning/phases/15-shallow-site-crawl/15-01-SUMMARY.md` — confirms POST /crawl and GET /crawl/test implemented and deployed
- `.planning/phases/10-mcp-server-update-npm-publish/10-02-PLAN.md` — exact npm publish pipeline, `autonomous: false` for publish step, two-commit workflow
- `npm pack --dry-run` (run 2026-03-18) — confirms exactly 5 files in tarball, version 1.1.0
- `npm whoami` (run 2026-03-18) — confirmed `jameswilliamwisdom`, auth active

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-05 requirement text, out-of-scope list (npm rename to bismuth-*)
- `.planning/STATE.md` — Phase 15 complete, publish gate requirement
- `.planning/PROJECT.md` — passkey auth note, locked decisions for x402 tool names and env var

### Tertiary (LOW confidence)
- npm semver docs: `^` range operator not crossing major versions — standard behavior, well-established

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH — all findings from direct source inspection, confirmed against Phase 10/13/14 precedents
- PITFALLS: HIGH — all findings from direct source inspection plus Phase 10 publish precedent

**Research date:** 2026-03-18
**Valid until:** Phase 16 execution (same day) — version strings and auth state are time-sensitive
**Dimensions researched:** INTEGRATION, PITFALLS
