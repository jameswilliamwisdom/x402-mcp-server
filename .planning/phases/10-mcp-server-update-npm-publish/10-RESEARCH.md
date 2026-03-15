# Phase 10: MCP Server Update + npm Publish - Research

**Researched:** 2026-03-15
**Domain:** TypeScript MCP Server, npm publish workflow
**Confidence:** HIGH — all findings derived from direct source code inspection (src/index.ts, backend main.py files, package.json)
**Method:** MECE decomposition (3 dimensions: PATTERNS, INTEGRATION, PITFALLS)

---

## Summary

Phase 10 adds 4 new APIS dict entries (scraping, conversion, search, transcription — email already exists from Phase 8) and registers 4 new tool handlers plus reviews `x402_send_email` for consistency, bringing the server to 11 tools total. All five tools follow the same pattern already established in `src/index.ts`: APIS dict entry → `apiPost` for paid mode → `apiGet` for free-test mode → `textResult` / `errorResult` helpers. The `x402_network_info` health check loop iterates `Object.entries(APIS)` dynamically, so adding the 4 new dict entries automatically expands coverage to all 8 APIs without any code change to the health check handler itself.

The npm publish workflow has two critical preconditions: the `files` whitelist in `package.json` must not be altered (it ensures only `dist/`, `README.md`, and `LICENSE` are published), and the version string must be bumped in both `package.json` AND the `McpServer` constructor in `src/index.ts`. The README currently documents 6 tools and must be updated to all 11 before publish. The standard pre-publish sequence is: commit source changes → build → verify with `npm pack --dry-run` → `npm whoami` → `npm publish` → `git tag v1.1.0`.

There is one price conflict between dimension research: DIM-PATTERNS proposed `$0.01` for scraping and conversion, but DIM-INTEGRATION extracted actual `@pay()` decorator values from backend source (`$0.02` for scraping, `$0.02` for conversion, `$0.01` for search, `$0.05` for transcription). DIM-INTEGRATION values are authoritative — use those.

**Primary recommendation:** Add 4 APIS dict entries, register 4 new tools following the `x402_send_email` pattern exactly, reduce health check timeout to 3000ms, update README to 11 tools, then run the 5-step pre-publish verification sequence.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- Follow existing `x402_` prefix pattern in src/index.ts — Claude picks best verb_noun names based on existing conventions
- Claude decides whether to include pricing info in tool descriptions
- Claude decides which tools need limit/latency warnings in descriptions (transcription at minimum per roadmap)
- Review existing x402_send_email tool for consistency with the other 4 new tools — update if needed
- Claude decides tool listing format (flat table vs grouped by category) based on readability for 11 tools
- Claude decides whether to include usage examples
- Do not mention dotenvx in README — it's a personal workflow, not required for package users
- Claude decides whether to include a "What's New in 1.1.0" changelog section
- Claude decides health check approach (parallel vs sequential) for all 8 APIs
- Claude decides response format (status+URL+price vs status+URL only)
- Claude decides whether to distinguish home-server (transcription) from Railway APIs
- Claude decides failure reporting (show 'down' vs omit unreachable)
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | 5 new tools registered in src/index.ts with Zod validation | PATTERNS: tool registration pattern, Zod schema conventions, handler body structure. INTEGRATION: exact endpoint contracts, request/response shapes, parameter constraints for all 4 new tools + email review. |
| MCP-02 | npm publish as x402-mcp-server@1.1.0 | PITFALLS: full publish workflow — version bump in 2 places, `npm pack --dry-run` secrets check, `npm whoami` auth check, README update, commit sequence, git tag v1.1.0. |
| MCP-03 | x402_network_info tool updated with health checks for all 8 APIs | PATTERNS: x402_network_info automatically expands when APIS dict entries are added (loop is over Object.entries(APIS) — no handler change needed). PITFALLS: reduce timeout to 3000ms for 8-API coverage, distinguish home server availability. |

</phase_requirements>

---

## Standard Stack

**Runtime dependencies (unchanged from current package.json):**
- `@modelcontextprotocol/sdk` — MCP server framework, `McpServer`, `StdioServerTransport`
- `zod` v4 — schema validation for all tool parameters
- `x402-fetch` — payment-wrapped fetch (wraps `node-fetch` with x402 challenge-response)

**Dev dependencies (unchanged):**
- `typescript` — compilation
- `tsx` — local development runner

**Build output:** `dist/index.js` (CommonJS, shebang injected by `postbuild` script) + `dist/index.d.ts`

**Key observation:** No new dependencies are needed for Phase 10. All 4 new tools use the existing `apiGet` / `apiPost` helpers. The existing Zod v4 patterns (`z.string()`, `z.number()`, `z.boolean()`, `z.enum()`, `z.array()`, `.optional()`, `.default()`) cover all new tool params without introducing any v4-only API surface that might conflict with the MCP SDK's internal zod v3 assumptions.

---

## Architecture Patterns

### Pattern 1: File Structure

`src/index.ts` is a single-file MCP server. All tools, helpers, and config live in one file with clearly delineated sections separated by ASCII banner comments:

```
// ─── API Endpoints ────────────────────────────
// ─── Config ───────────────────────────────────
// ─── Payment-wrapped fetch ────────────────────
// ─── Helpers ──────────────────────────────────
// ─── MCP Server ───────────────────────────────
// ─── Tool: x402_network_info (FREE) ──────────
// ─── Tool: x402_screenshot ────────────────────
// ... one banner per tool ...
// ─── Start ────────────────────────────────────
```

Each new tool gets one banner-comment section in the tool block. Each new API gets one entry in the `APIS` dict.

---

### Pattern 2: APIS Dict Entry

Every backend service has an entry in the `APIS` constant. This is the single source of truth for base URLs used in handlers and in `x402_network_info`. New entries follow the existing shape exactly:

```typescript
const APIS = {
  // ... existing entries ...
  scraping: {
    name: "Scraping API",
    baseUrl: "https://x402-scraping-api-production.up.railway.app",
    price: "$0.02",
    description: "Scrape any URL and return structured JSON: markdown, links, tables, images, metadata",
    usesX402: true,
  },
  conversion: {
    name: "Conversion API",
    baseUrl: "https://x402-conversion-api-production.up.railway.app",
    price: "$0.02",
    description: "Convert files: image resize/reformat, CSV to JSON, HTML to PDF",
    usesX402: true,
  },
  search: {
    name: "Search API",
    baseUrl: "https://x402-search-api-production.up.railway.app",
    price: "$0.01",
    description: "Web search via Tavily — ranked results with title, URL, snippet, score",
    usesX402: true,
  },
  transcription: {
    name: "Transcription API",
    baseUrl: "https://transcribe.jameswisdom.ink",
    price: "$0.05",
    description: "Transcribe audio from any URL — auto language detection, word timestamps, 25MB/10min limits",
    usesX402: true,
  },
} as const;
```

**Critical:** The `email` key already exists from Phase 8. Do NOT add a duplicate. Only 4 new entries are needed. The `} as const` close must remain intact after editing — TypeScript uses literal types derived from it.

---

### Pattern 3: apiGet / apiPost Helpers

All HTTP calls go through two existing helpers:

```typescript
// GET — used for free-test endpoints (no body)
async function apiGet(baseUrl: string, path: string, usePayment = false)

// POST — used for paid endpoints (with JSON body)
async function apiPost(
  baseUrl: string,
  path: string,
  body: Record<string, unknown>,
  usePayment = false
)
```

- Paid mode: pass `true` as the `usePayment` arg
- Free mode: omit `usePayment` (defaults `false`) — never pass `true` for free-test calls
- Both throw `Error("API ${status}: ${body}")` on non-2xx responses
- Both return the parsed JSON response directly

---

### Pattern 4: Tool Handler Body

Every handler follows the same branching structure. The `x402_send_email` tool (newest) is the canonical reference:

```typescript
async (params) => {
  const base = APIS.<key>.baseUrl;  // always reference APIS dict

  try {
    const usePaid = !!PRIVATE_KEY;

    if (usePaid) {
      const payload: Record<string, unknown> = {
        required_field: params.required_field,
      };
      if (params.optional_field) payload.optional_field = params.optional_field;

      const data = await apiPost(base, "/endpoint", payload, true);
      return textResult({ mode: "paid", cost: "$X.XX", ...data });
    } else {
      const data = await apiGet(base, "/endpoint/test");
      return textResult({
        mode: "free_test",
        note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for real <operation>.",
        ...data,
      });
    }
  } catch (err: any) {
    return errorResult(err.message);
  }
}
```

**Rules:**
- `const base = APIS.<key>.baseUrl` — always, never hardcode URL in handler
- `const usePaid = !!PRIVATE_KEY` — PRIVATE_KEY is module-level
- Paid: `apiPost(base, "/endpoint", payload, true)` with `cost` field in response
- Free: `apiGet(base, "/endpoint/test")` with `note` field explaining limitation
- Optional params: build mutable `payload` object, conditionally append
- All errors fall through to outer `catch` → `errorResult(err.message)`

---

### Pattern 5: x402_network_info Auto-Expansion

The health check tool iterates `Object.entries(APIS)` — adding 4 new APIS dict entries is the only work needed to expand it to all 8 APIs. No changes to the handler body are needed.

Current `checkHealth` function: tries `/health` first (5s timeout), falls back to `/`. For 1.1.0, reduce the `AbortSignal.timeout` from `5000` to `3000` to keep `x402_network_info` responsive with 8 parallel checks.

---

### Pattern 6: Tool Registration Signature

```typescript
server.tool(
  "x402_<verb>_<noun>",
  `One-sentence what-it-does.
Price: $X.XX USDC per call (paid mode) | Free test: returns fixture data.

Additional capability or limit details.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: <what the JSON response contains>.`,
  {
    param_name: z.string().url().describe("Description of this param"),
    optional_param: z.string().optional().describe("Optional param (default: none)"),
  },
  async (params) => { /* handler */ }
);
```

- Every param gets `.describe("...")`
- Defaults inline with `.default(value)` — no need to handle `undefined` in handler
- Optional params use `.optional()` — check with `if (params.optional_param)` before payload

---

### Pattern 7: textResult / errorResult Helpers

```typescript
function textResult(data: unknown) {
  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return { content: [{ type: "text" as const, text }] };
}

function errorResult(message: string) {
  return {
    content: [{ type: "text" as const, text: `Error: ${message}` }],
    isError: true,
  };
}
```

Always use these — never return raw objects.

---

### Pattern 8: Version Bump

```typescript
// src/index.ts — line ~158
const server = new McpServer({
  name: "x402-api-network",
  version: "1.1.0",   // bump from "1.0.0"
});
```

Must match `package.json` `"version": "1.1.0"`. These are not linked automatically.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Pre-publish tarball verification | Custom file listing script | `npm pack --dry-run` — shows exactly what npm will publish |
| npm auth verification | Manual token inspection | `npm whoami` — expected output: `jameswilliamwisdom` |
| Semantic version management | Manual string editing in 2 files | `npm version minor` — updates `package.json` + git commit + git tag atomically (use `--no-git-tag-version` if controlling tag timing manually) |
| Post-publish verification | Manual registry check | `npm view x402-mcp-server@1.1.0` — confirms registry received correct version |
| Secret scanning before publish | Custom grep | `npm pack` then `tar -tzf x402-mcp-server-1.1.0.tgz` — the tarball IS the truth |
| Payment auth + retry logic | Custom x402 challenge-response | `x402-fetch` library (already in use) — handles all HTTP 402 challenge/response |
| HTTP error handling | Per-tool try/catch | Existing `apiGet`/`apiPost` helpers — already handle all non-2xx as thrown errors |
| Health check parallelism | Manual Promise.all chaining | Existing `Promise.allSettled` in `checkHealth` loop — already parallel |

---

## Common Pitfalls

### Pitfall 1: Duplicate `email` Entry in APIS Dict

The phase description says "5 new APIS dict entries" but `email` was already added in Phase 8. Only 4 new entries are needed: `scraping`, `conversion`, `search`, `transcription`. Adding a second `email` key causes a TypeScript error or silent shadowing.

**Fix:** Confirm `email` key present before editing. Add exactly 4 new keys.

---

### Pitfall 2: Wrong Prices in APIS Dict

DIM-PATTERNS initially had `$0.01` for scraping and conversion. The actual `@pay()` decorators in backend source are `$0.02` for both. The authoritative values (from backend `config.py` and `main.py`):
- Scraping: `$0.02`
- Conversion: `$0.02`
- Search: `$0.01`
- Transcription: `$0.05`

**Fix:** Use the values above. Use DIM-INTEGRATION as the price authority.

---

### Pitfall 3: Version Bump in Only One Place

`package.json` `"version"` and `McpServer({ version: "..." })` are not linked. MCP clients reporting server version via `initialize` handshake see the constructor value, not `package.json`. Both must read `"1.1.0"`.

**Fix:** Update both in the same task. Check `src/index.ts` line ~158.

---

### Pitfall 4: Hardcoding baseUrl in Handler

Putting the Railway URL string directly in the handler instead of `APIS.<key>.baseUrl` bypasses the single source of truth that `x402_network_info` also reads.

**Fix:** Always `const base = APIS.<key>.baseUrl` at the top of every handler.

---

### Pitfall 5: Free Test Endpoint Uses POST Instead of GET

Free test endpoints use `apiGet(base, "/endpoint/test")` with no body — same pattern as `x402_send_email`'s `apiGet(base, "/send/test")`. Copying the paid-mode `apiPost` call for free mode will hit a 405 Method Not Allowed on backends that only accept GET at their test routes.

**Fix:** Free mode always uses `apiGet`. Paid mode uses `apiPost` (for these 4 new tools).

---

### Pitfall 6: .env Leaked to npm Tarball

npm does NOT automatically exclude `.env` files. This project is safe because `package.json` uses a `files` whitelist (`["dist", "README.md", "LICENSE"]`), but that whitelist must not be broadened.

**Fix:** Do not alter the `files` array. Do not create a `.npmignore` (it would silently disable `.gitignore` as fallback). Run `npm pack --dry-run` — expect exactly 5 files: `dist/index.js`, `dist/index.d.ts`, `README.md`, `LICENSE`, `package.json`.

---

### Pitfall 7: The `.npmignore` Trap

Creating a `.npmignore` silently disables `.gitignore` as fallback. npm uses `.npmignore` exclusively when it exists — `.gitignore` is completely ignored. Files listed in `.gitignore` but not `.npmignore` will be published.

**Fix:** Do not create `.npmignore`. The `files` whitelist approach already in place is safer.

---

### Pitfall 8: Stale dist/ at Publish Time

`prepublishOnly` runs `tsc`, but if source has logical errors not caught at compile time, the published artifact reflects those errors. The `postbuild` shebang injection must remain active — without `#!/usr/bin/env node` at line 1, `npx x402-mcp-server` fails silently on some systems.

**Fix:** Run `npm run build` manually before `npm publish`. Verify `head -1 dist/index.js` outputs `#!/usr/bin/env node`. Run `node dist/index.js` to confirm it starts without errors.

---

### Pitfall 9: Publishing with Uncommitted src/

Publishing before committing `src/index.ts` means the npm artifact (`dist/`) and GitHub source diverge. The `v1.1.0` tag captures an intermediate state.

**Fix:** Commit sequence: (1) commit `src/index.ts`, `package.json`, `README.md` changes; (2) `npm run build`; (3) commit `dist/`; (4) `npm publish`; (5) `git tag v1.1.0`.

---

### Pitfall 10: README Not Updated Before Publish

The README currently documents 6 tools (`x402_network_info`, `x402_screenshot`, `x402_pdf_extract`, `x402_sentiment`, `x402_market_overview`, `x402_intelligence`). `x402_send_email` (Phase 8) and the 4 new tools are missing — 11 tools total must be documented. The README is included in the tarball via `files: ["README.md"]` and is what npmjs.com shows.

**Fix:** Update README tool table to all 11 tools before `npm publish`.

---

### Pitfall 11: package.json description and keywords Are Stale

Current `description`: `"MCP server for the x402 API Network — screenshot, PDF extraction, and crypto sentiment tools with USDC micropayments on Base"` — only mentions 3 of 8 capabilities. Current `keywords` missing: `"web-scraping"`, `"email"`, `"web-search"`, `"file-conversion"`, `"transcription"`.

**Fix:** Update `description` and `keywords` as part of the version bump commit (Claude's discretion per CONTEXT.md).

---

### Pitfall 12: x402_network_info Timeout With 8 APIs

`checkHealth()` uses a `/` fallback if `/health` returns non-OK, potentially doubling worst-case latency (2 HTTP requests × 5s timeout = up to 10s per failing API). With 8 APIs in parallel, any one failing API dominates the wall time.

**Fix:** Reduce `AbortSignal.timeout` from `5000` to `3000` for both fetches in `checkHealth`. All new APIs (Railway) respond on `/health` — the fallback is only needed for unusual edge cases.

---

### Pitfall 13: Transcription Home Server Variable Uptime

`transcribe.jameswisdom.ink` runs on a home server via Cloudflare Tunnel and is the only non-Railway service. It goes offline during host restarts, sleep mode, and Cloudflare Tunnel gaps. The health check will legitimately show `"offline"` more often than Railway services.

**Fix:** In `x402_network_info`, distinguish the transcription API from Railway services — per CONTEXT.md, Claude decides whether to add a `note: "Home server — uptime varies"` field. Also document 30–120s latency in the tool description.

---

### Pitfall 14: Conversion API `type` Field Is Required

The conversion API's Pydantic model uses a discriminated union on `type`. Sending `POST /convert` without `type` returns a 422 validation error. The `type` field is not optional.

**Fix:** Always include `type` in the conversion payload. The Zod schema `z.enum(["image", "csv", "html_pdf"])` enforces this at the MCP layer.

---

### Pitfall 15: Conversion API Returns base64, Not a URL

The `data` field in a successful conversion response is raw base64-encoded bytes of the output file — not a URL or file path. The API is stateless; there is no file storage.

**Fix:** Tool description must clearly state "Returns base64-encoded output bytes with MIME type." Callers must decode to use the file.

---

### Pitfall 16: Search `answer` Field Conditionally Present

When `include_answer: false` (default), the `answer` key is entirely absent from the response. When `include_answer: true`, the `answer` key is present but may be `null` if Tavily cannot synthesize one. Rate limit: 50 queries per wallet per day — HTTP 429 on breach.

**Fix:** Tool description should document the conditional presence and daily limit.

---

### Pitfall 17: Sending `null` for Optional Params

Sending `{ "language": null }` is different from omitting the key. Pydantic handles both, but conditional payload building is cleaner and matches the existing `x402_send_email` pattern.

**Fix:** Always build payload conditionally:
```typescript
if (params.language) payload.language = params.language;
```
Never spread full `params` into the payload.

---

### Pitfall 18: `as const` Accidentally Removed During APIS Edit

TypeScript infers non-literal types if `} as const;` is accidentally deleted during the APIS dict edit.

**Fix:** After editing, confirm the closing `} as const;` is still present on the APIS object.

---

### Pitfall 19: npm publish Is Irreversible

npm allows unpublish within 72 hours for packages with no dependents. After that, the version is permanent.

**Fix:** Full pre-publish checklist: (1) `npm pack --dry-run` — verify 5 files only; (2) `npm run build && node dist/index.js` — verify artifact starts; (3) `npm whoami` — verify `jameswilliamwisdom`; (4) inspect tarball with `tar -tzf x402-mcp-server-1.1.0.tgz` if any doubt; (5) only then `npm publish`.

---

## Code Examples

### Complete Tool: x402_scrape_url

```typescript
// ─── Tool: x402_scrape_url ──────────────────────────────────────────────────

server.tool(
  "x402_scrape_url",
  `Scrape a web page and return structured JSON with markdown content, links, tables, images, and metadata.
Price: $0.02 USDC per scrape (paid mode) | Free test: returns fixture data.

Supports JS-rendered pages via Playwright. Optional wait_for CSS selector for async SPA content.
Hard timeout: 8 seconds total (page load + selector wait combined).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: markdown text, extracted links, tables, images, page metadata, and success/failure status.`,
  {
    url: z.string().url().describe("URL to scrape (http/https, max 2048 chars)"),
    wait_for: z.string().max(500).optional()
      .describe("CSS selector to wait for before extracting (for SPAs, e.g. '.article-body')"),
  },
  async (params) => {
    const base = APIS.scraping.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = { url: params.url };
        if (params.wait_for) payload.wait_for = params.wait_for;
        const data = await apiPost(base, "/scrape", payload, true);
        return textResult({ mode: "paid", cost: "$0.02", ...data });
      } else {
        const data = await apiGet(base, "/scrape/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live scraping.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

---

### Complete Tool: x402_convert_file

```typescript
// ─── Tool: x402_convert_file ────────────────────────────────────────────────

server.tool(
  "x402_convert_file",
  `Convert files between formats — image resize/reformat, CSV to JSON, or HTML to PDF.
Price: $0.02 USDC per conversion (paid mode) | Free test: returns fixture data.

Supported conversions:
- image: resize/reformat an image from a URL (Pillow) — outputs base64-encoded bytes
- csv: convert a CSV URL to JSON array
- html_pdf: render HTML from a URL to PDF — outputs base64-encoded bytes

Input limit: 10MB source file. Output limit: 8MB (before base64 encoding).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: base64-encoded output bytes with MIME type, or JSON array for csv type.`,
  {
    url: z.string().url().describe("URL of the file to convert (public, http/https, max 10MB)"),
    type: z.enum(["image", "csv", "html_pdf"])
      .describe("Conversion type: image (resize/reformat), csv (CSV to JSON), html_pdf (HTML to PDF)"),
    format: z.enum(["jpeg", "png", "webp", "gif"]).optional()
      .describe("Output image format (only for type='image', default: jpeg)"),
    width: z.number().int().min(1).max(8000).optional()
      .describe("Target width in pixels (only for type='image', preserves aspect ratio if height omitted)"),
    height: z.number().int().min(1).max(8000).optional()
      .describe("Target height in pixels (only for type='image', preserves aspect ratio if width omitted)"),
  },
  async (params) => {
    const base = APIS.conversion.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = { type: params.type, url: params.url };
        if (params.format !== undefined) payload.format = params.format;
        if (params.width !== undefined) payload.width = params.width;
        if (params.height !== undefined) payload.height = params.height;
        const data = await apiPost(base, "/convert", payload, true);
        return textResult({ mode: "paid", cost: "$0.02", ...data });
      } else {
        const data = await apiGet(base, "/convert/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live conversion.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

---

### Complete Tool: x402_web_search

```typescript
// ─── Tool: x402_web_search ──────────────────────────────────────────────────

server.tool(
  "x402_web_search",
  `Search the web and return ranked results via Tavily — title, URL, snippet, and relevance score.
Price: $0.01 USDC per search (paid mode) | Free test: returns fixture data.

Optional synthesized answer summarizing results. Use include_domains/exclude_domains for focused research.
Per-wallet daily limit: 50 queries (resets midnight UTC).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: query, results array (title, url, snippet, score), optional answer field.`,
  {
    query: z.string().min(1).max(400).describe("Search query (max 400 chars)"),
    max_results: z.number().int().min(1).max(10).default(5)
      .describe("Number of results to return (1-10, default: 5)"),
    include_answer: z.boolean().default(false)
      .describe("Include a synthesized answer above the results (may be null if Tavily cannot synthesize)"),
    include_domains: z.array(z.string()).max(20).optional()
      .describe("Restrict results to these domains only (max 20)"),
    exclude_domains: z.array(z.string()).max(20).optional()
      .describe("Exclude these domains from results (max 20)"),
  },
  async (params) => {
    const base = APIS.search.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = {
          query: params.query,
          max_results: params.max_results,
          include_answer: params.include_answer,
        };
        if (params.include_domains) payload.include_domains = params.include_domains;
        if (params.exclude_domains) payload.exclude_domains = params.exclude_domains;
        const data = await apiPost(base, "/search", payload, true);
        return textResult({ mode: "paid", cost: "$0.01", ...data });
      } else {
        const data = await apiGet(base, "/search/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live web search.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

---

### Complete Tool: x402_transcribe_audio

```typescript
// ─── Tool: x402_transcribe_audio ────────────────────────────────────────────

server.tool(
  "x402_transcribe_audio",
  `Transcribe an audio file from a URL using faster-whisper with auto language detection.
Price: $0.05 USDC per transcription (paid mode) | Free test: returns fixture data.

Supports: MP3, WAV, M4A, FLAC, OGG, and most audio formats.
Limits: 25MB file size, 10-minute duration. Payment is charged on download; duration refusals are still charged.
Note: transcription can take 30–120 seconds for longer files (CPU-based, requests queue serially).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: transcript text, detected language, language confidence, duration, and segment or word timestamps.`,
  {
    url: z.string().url().describe("URL of the audio file to transcribe (public, http/https, max 25MB, max 10 min)"),
    language: z.string().optional()
      .describe("ISO 639-1 language hint (e.g. 'en', 'fr', 'es') — omit for auto-detection"),
    word_timestamps: z.boolean().default(false)
      .describe("Return word-level timestamps instead of segment-level (default: false)"),
  },
  async (params) => {
    const base = APIS.transcription.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      if (usePaid) {
        const payload: Record<string, unknown> = {
          url: params.url,
          word_timestamps: params.word_timestamps,
        };
        if (params.language) payload.language = params.language;
        const data = await apiPost(base, "/transcribe", payload, true);
        return textResult({ mode: "paid", cost: "$0.05", ...data });
      } else {
        const data = await apiGet(base, "/transcribe/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for real audio transcription.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

---

### Pre-Publish Verification Sequence

```bash
# 1. Verify tarball contents
npm pack --dry-run
# Expect exactly: dist/index.js, dist/index.d.ts, README.md, LICENSE, package.json

# 2. Build and verify the artifact
npm run build
head -1 dist/index.js  # Must output: #!/usr/bin/env node
node dist/index.js     # Must start without errors (Ctrl+C to stop)

# 3. Verify npm auth
npm whoami             # Must output: jameswilliamwisdom

# 4. Optional: inspect actual tarball if any doubt
npm pack               # Creates x402-mcp-server-1.1.0.tgz
tar -tzf x402-mcp-server-1.1.0.tgz
rm x402-mcp-server-1.1.0.tgz  # Clean up

# 5. Publish
npm publish

# 6. Verify publish succeeded
npm view x402-mcp-server@1.1.0

# 7. Tag
git tag v1.1.0
git push origin v1.1.0
```

---

## State of the Art

**x402 protocol:** HTTP 402 Payment Required flow — server issues challenge, client pays via EVM wallet on Base (L2 Ethereum) using USDC, then retries. The `x402-fetch` library handles all challenge-response negotiation. Existing pattern in this project is current with the spec.

**MCP SDK:** `@modelcontextprotocol/sdk` is the official Anthropic SDK for building MCP servers. The `McpServer` class and `StdioServerTransport` are the stable API for this use case. No changes to MCP SDK usage are needed.

**npm publish workflow:** The `files` whitelist approach is the current best practice for npm publish security over `.npmignore` blacklisting. `npm pack --dry-run` is the standard verification step. No third-party release tooling (np, semantic-release, release-it) is needed for a manual single-package publish at this scale.

**Tool count:** After Phase 10, this server exposes 11 tools, well within MCP client capability. No tool grouping, pagination, or lazy registration is needed.

---

## Open Questions

1. **Should `x402_send_email` be reviewed for description consistency?** CONTEXT.md says "Review existing x402_send_email tool for consistency with the other 4 new tools — update if needed." The tool is functionally correct per DIM-INTEGRATION cross-check, but the description format may differ from the new tools' descriptions. Low risk — leave to planner's discretion.

2. **Health check timeout reduction:** Reducing `AbortSignal.timeout` from 5000ms to 3000ms is recommended by DIM-PITFALLS. This is a one-line change inside `checkHealth()`. The planner should decide whether to make this a separate task or fold it into the APIS dict expansion task.

3. **Transcription home server note in network_info response:** Should `x402_network_info` add a `"note": "Home server — uptime varies"` field specifically for the transcription entry? Claude's discretion per CONTEXT.md.

4. **README format:** 11 tools — flat table or grouped by category? Claude's discretion per CONTEXT.md.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | WARN | Price conflict resolved: DIM-PATTERNS had `$0.01` for scraping/conversion; DIM-INTEGRATION (backend source) has `$0.02`. DIM-INTEGRATION is authoritative. All other findings agree across dimensions. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Optional sections present: User Constraints, Phase Requirements, State of the Art, Open Questions. |
| Dimension Coverage | PASS | PATTERNS findings: APIS dict pattern, apiGet/apiPost helpers, tool registration, handler body, network_info, Zod conventions, textResult/errorResult, x402_send_email reference — all integrated. INTEGRATION findings: endpoint contracts for all 4 APIs, request/response shapes, email cross-check — all integrated. PITFALLS findings: .env/files whitelist safety, .npmignore trap, stale dist, version bump in 2 places, npm auth, uncommitted src, network_info timeout, home server reliability, README update, stale metadata, irreversible publish, Zod v4 compatibility note — all integrated. |
| Requirement Coverage | PASS | MCP-01 → Architecture Patterns (tool registration) + Code Examples (4 complete tools) + Integration contracts. MCP-02 → Don't Hand-Roll (npm tooling) + Common Pitfalls (publish workflow). MCP-03 → Pattern 5 (auto-expansion via APIS dict loop) + Pitfall 12 (timeout reduction). |

---

## Sources

### Primary (HIGH confidence)
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — authoritative source for all pattern findings; all existing tool registrations, APIS dict shape, apiGet/apiPost helpers, checkHealth, textResult/errorResult
- `/Users/jameswisdom/projects/x402-mcp-server/package.json` — files whitelist, version, description, keywords, build scripts, dependencies
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — scraping endpoint contracts, request/response shapes
- `/Users/jameswisdom/projects/x402-mcp-server/x402-conversion-api/main.py` — conversion discriminated union, endpoint contracts, response shapes
- `/Users/jameswisdom/projects/x402-mcp-server/x402-search-api/main.py` — search endpoint contracts, rate limit shape
- `/Users/jameswisdom/projects/x402-mcp-server/x402-email-api/main.py` — email endpoint contracts (existing x402_send_email cross-check)
- `/Users/jameswisdom/projects/x402-mcp-server/x402-transcription-api/main.py` — transcription endpoint contracts, response shapes
- `/Users/jameswisdom/projects/x402-mcp-server/x402-transcription-api/config.py` — PRICE_PER_REQUEST = "$0.05", file/duration limits
- `npm pack --dry-run` output — confirmed 5 files only: dist/index.js, dist/index.d.ts, README.md, LICENSE, package.json
- `.planning/phases/10-mcp-server-update-npm-publish/10-CONTEXT.md` — locked decisions and production URLs

### Secondary (MEDIUM confidence)
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/STATE.md` — Phase 8 wired email, production URL list, accumulated decisions
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/REQUIREMENTS.md` — TRANS-05 size/duration limits inform transcription tool description
- npm Blog: "Publishing what you mean to publish" — files field whitelist approach, .npmignore/gitignore interaction rules
- Node Best Practices: "Avoid publishing secrets" — .env leak patterns, whitelist recommendation
- npm/cli Wiki: "Files & Ignores" — precedence: files > .npmignore > .gitignore

### Tertiary (LOW confidence)
- WebSearch: MCP server duplicate tool name discussion — confirms `x402_` prefix avoids cross-server collisions
- WebSearch: README update requires version bump — confirms README changes only take effect with new publish

---

## Metadata

**Confidence breakdown:**
- PATTERNS: HIGH (direct src/index.ts inspection)
- INTEGRATION: HIGH (direct backend main.py inspection, config.py for prices)
- PITFALLS: HIGH (direct package.json inspection, npm pack --dry-run verification)
- Overall: HIGH

**Conflict resolved:** PATTERNS vs INTEGRATION price values — INTEGRATION (backend source) is authoritative

**Research date:** 2026-03-15
**Valid until:** Until any backend `@pay()` decorator changes (price values) or MCP SDK major version bump
**Dimensions researched:** 3 (PATTERNS, INTEGRATION, PITFALLS)
**Nyquist validation:** Disabled
