# Phase 2: npm Publish - Research

**Researched:** 2026-03-10
**Domain:** GitHub repo creation, npx GitHub direct install, README documentation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Distribution: GitHub direct install for v1.0 — `npx -y github:jameswilliamwisdom/x402-mcp-server`
- npm registry publish deferred until npm account issues resolved
- GitHub repo: public, under `jameswilliamwisdom` username, name `x402-mcp-server`
- README: Comprehensive, all 6 tools with descriptions + pricing, quick start (free + paid), config JSON, env var setup, links to brand site
- Developer-focused tone — straight to the point, no marketing fluff
- Badges: shields.io GitHub badges (not npm badges — not published yet)
- Include configs for ALL major clients: Claude Desktop, Claude Code, Cursor, Windsurf
- All configs use `npx -y github:jameswilliamwisdom/x402-mcp-server`
- Env var (X402_PRIVATE_KEY) referenced via .env file, not inline in config JSON
- Free mode config shown separately (no env var needed)
- Show free mode first (lower barrier to entry)

### Claude's Discretion
- README section ordering
- Badge selection and styling
- Exact formatting of tool/pricing table
- How to structure the free vs paid mode sections

### Deferred Ideas (OUT OF SCOPE)
- npm registry publish (defer until npm account resolved). When ready: `npm publish --access public`, update README install commands
- npm badges (won't work until published)
- Git tag `v1.0.0` (defer until npm publish)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NPM-01 | README updated with npm install instructions and Claude config example (using `npx -y`) | README structure, MCP config formats for all 4 clients, badge syntax, free/paid mode sections |
| NPM-02 | Package published to npm registry as `x402-mcp-server` — DEFERRED | Deferred per user decision. No npm publish action needed for v1.0 |
</phase_requirements>

## Summary

Phase 2 is primarily a documentation and repository publication phase. The core technical work splits into two parts: (1) creating the GitHub repository and getting the codebase published publicly, and (2) rewriting the README to be comprehensive and installation-ready.

The most critical non-obvious finding is that **`dist/` must be committed to the git repository** for `npx -y github:jameswilliamwisdom/x402-mcp-server` to work reliably. The current `.gitignore` excludes `dist/`, which means the compiled `dist/index.js` that `bin` points to would not exist when someone installs via GitHub. npm's `prepare` lifecycle hook for git dependencies is documented to run on GitHub installs, but multiple npm/cli GitHub issues (some from 2026, some marked Wontfix) confirm it is unreliable in practice — particularly for TypeScript packages needing devDependencies during the build step. The safe, battle-tested approach is to commit the compiled output.

The `gh` CLI is installed (v2.87.2) and authenticated as `jameswilliamwisdom`, making repo creation a single command. No remote is configured yet on the local git repo. The repo `x402-mcp-server` does not yet exist on GitHub under this account.

**Primary recommendation:** Remove `dist/` from `.gitignore`, commit the built output, create the GitHub repo via `gh repo create`, push, then write the README. In that order — so the repo exists and the install command works before the README documents it.

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `gh` CLI | 2.87.2 (installed) | Create GitHub repo, set visibility, push | Official GitHub CLI; single command repo creation |
| `git` | system | Commit dist/, push to remote | VCS; already initialized with history |
| Markdown | — | README format | GitHub renders natively |
| shields.io | — | Badges in README | Standard badge service; no npm publish required |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `npm run build` | — | Rebuild dist/ if stale | Before committing dist/ to ensure it is current |
| `npx` | npm built-in | End-user install mechanism | GitHub direct install via `npx -y github:user/repo` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Commit dist/ to git | `prepare` script to build on install | `prepare` on git deps is buggy in npm (multiple open issues, some Wontfix) — unreliable for TypeScript |
| `gh repo create` | GitHub UI | CLI is faster and scriptable |
| shields.io GitHub badges | npm version badges | npm badges require published package; shields.io GitHub badges work immediately |

## Architecture Patterns

### Pattern 1: GitHub Direct Install via npx

**What:** `npx -y github:jameswilliamwisdom/x402-mcp-server` fetches the repo from GitHub, runs npm install (no devDependencies), and executes the `bin` entry. The `-y` flag skips confirmation prompts — required for MCP config JSON.

**Critical requirement:** The `bin` field (`"x402-mcp-server": "dist/index.js"`) must point to a file that EXISTS in the GitHub repo. Since `dist/` is currently in `.gitignore`, it must be removed from `.gitignore` and the built `dist/index.js` committed.

**Why prepare script doesn't save you:**
- npm/cli issue #3692 (open as of Feb 2026): global install from git with prepare script + bin field deletes files after prepare runs
- npm/cli issue #8440 (July 2025): devDependencies not available during prepare, TypeScript compilation fails
- Multiple Wontfix issues going back to npm v7
- **Bottom line:** Do not rely on `prepare` for GitHub direct install reliability

**How to fix .gitignore:**
```
# Remove this line from .gitignore:
dist/
```
Then commit `dist/index.js` and `dist/index.d.ts`.

**What npx does step-by-step:**
1. Downloads repo tarball from GitHub
2. Runs `npm install` (production deps only by default — viem, x402-fetch, zod, @modelcontextprotocol/sdk)
3. Finds `bin["x402-mcp-server"]` → `dist/index.js`
4. Executes it via Node with `#!/usr/bin/env node` shebang (already present — confirmed)

### Pattern 2: GitHub Repo Creation with `gh` CLI

```bash
# Create public repo from local git
gh repo create x402-mcp-server --public --source=. --remote=origin --push

# Or in two steps:
gh repo create x402-mcp-server --public
git remote add origin https://github.com/jameswilliamwisdom/x402-mcp-server.git
git push -u origin main
```

The `--source=.` flag uses the current directory as the source. The `--push` flag does the initial push automatically. Authenticated as `jameswilliamwisdom` (confirmed via `gh auth status`).

### Pattern 3: MCP Client Config Format

All four clients use the same `mcpServers` JSON structure. Differences are config file location only.

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):
```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "github:jameswilliamwisdom/x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "${X402_PRIVATE_KEY}"
      }
    }
  }
}
```

**Claude Code** — via CLI (`claude mcp add`):
```bash
claude mcp add --transport stdio --env X402_PRIVATE_KEY=YOUR_KEY x402 -- npx -y github:jameswilliamwisdom/x402-mcp-server
```
Or via `~/.claude.json` (user scope) with the same mcpServers structure.

**Cursor** — `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "github:jameswilliamwisdom/x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "YOUR_PRIVATE_KEY"
      }
    }
  }
}
```

**Windsurf** — `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "github:jameswilliamwisdom/x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "YOUR_PRIVATE_KEY"
      }
    }
  }
}
```

**Free mode** (no env var — all 4 clients same pattern, just omit `env`):
```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "github:jameswilliamwisdom/x402-mcp-server"]
    }
  }
}
```

**Note on env vars:** CONTEXT.md specifies referencing `.env` file rather than inline values. In MCP JSON configs, there is no standard `.env` file interpolation — each client handles env differently. The README should tell users to replace `YOUR_PRIVATE_KEY` with their actual key, and optionally note that some clients support env var expansion via `${VAR}` syntax. Do not imply a `.env` file is auto-loaded by the MCP server process; env vars must be set in the config or the shell environment.

### Pattern 4: shields.io Badge Syntax

For v1.0 without npm publish, use GitHub-based badges:

```markdown
[![License: MIT](https://img.shields.io/github/license/jameswilliamwisdom/x402-mcp-server)](https://github.com/jameswilliamwisdom/x402-mcp-server/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/jameswilliamwisdom/x402-mcp-server?style=social)](https://github.com/jameswilliamwisdom/x402-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
```

The `node >=18` badge uses a static label since there is no auto-detection endpoint for engines field — the static badge is correct and matches `package.json`'s `engines.node: ">=18"`.

### Pattern 5: README Section Order (Recommended)

Based on developer-focused README conventions and the "free mode first" constraint:

1. Title + one-liner description
2. Badges (license, node version, stars)
3. Tools table (all 6 with price)
4. Quick Start — Free Mode (no wallet — lowest friction)
5. Quick Start — Paid Mode (with X402_PRIVATE_KEY)
6. MCP Client Configs (Claude Desktop, Claude Code, Cursor, Windsurf)
7. Env var / wallet setup (brief; link to brand site docs for full guide)
8. How it works (x402 protocol flow — 5 steps)
9. Free mode limitations (what's restricted without a key)
10. License

### Anti-Patterns to Avoid

- **Env var inline in README:** Never show `"X402_PRIVATE_KEY": "0xabc123..."` with a real key placeholder that looks like it should be committed to source. Make it obvious it belongs in the client's config only.
- **Omitting `-y` flag in npx commands:** MCP servers run stdio — interactive prompts break the transport. Every npx command in README must include `-y`.
- **Showing `node /path/to/dist/index.js` in config:** The current README does this — it's wrong for v1.0 install method. All configs must use `npx -y github:jameswilliamwisdom/x402-mcp-server`.
- **Committing dist/ without rebuilding first:** Run `npm run build` before removing dist/ from .gitignore and committing, to ensure dist/index.js is current with src/.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub repo creation | Manual UI flow | `gh repo create` | One command, handles remote setup |
| Badge service | Custom badge endpoint | shields.io | Battle-tested, zero maintenance |
| MCP config examples | Custom format | Standard mcpServers JSON | What all clients expect |

**Key insight:** This phase is entirely documentation + git operations. There is no custom code to write.

## Common Pitfalls

### Pitfall 1: dist/ not in git = npx install fails silently
**What goes wrong:** User runs `npx -y github:jameswilliamwisdom/x402-mcp-server` and gets `Error: Cannot find module '/path/dist/index.js'` or a broken MCP server that fails to start.
**Why it happens:** `.gitignore` excludes `dist/`. npm installs what's in the repo tarball. `prepare` script is unreliable for git deps.
**How to avoid:** Remove `dist/` from `.gitignore`. Run `npm run build`. Commit `dist/index.js` and `dist/index.d.ts`. Verify with `git ls-files dist/`.
**Warning signs:** After repo push, try `npx -y github:jameswilliamwisdom/x402-mcp-server` locally — if it fails with module not found, dist/ was not committed.

### Pitfall 2: Missing `-y` flag breaks MCP stdio transport
**What goes wrong:** MCP server never starts; client shows connection error. npx asks "Install package? (y)" and blocks on stdin — which MCP has taken over.
**Why it happens:** npx without `-y` prompts for confirmation on first run.
**How to avoid:** Every `npx` invocation in README must be `npx -y`. Grep README for `npx ` without `-y` before finalizing.
**Warning signs:** Connection errors in MCP client that disappear when user confirms the prompt manually.

### Pitfall 3: README shows old local file path config
**What goes wrong:** Users copy the config and it breaks — `node /path/to/x402-mcp-server/dist/index.js` requires a local clone.
**Why it happens:** Current README shows `"command": "node"` with a local path. This was placeholder for pre-publish.
**How to avoid:** Replace all client config examples with `npx -y github:jameswilliamwisdom/x402-mcp-server`. The old local path config can go entirely.

### Pitfall 4: npm package name distinction in README
**What goes wrong:** Users install `@x402/fetch` instead of `x402-fetch` and it fails (the scoped package is a stub placeholder).
**Why it happens:** x402 ecosystem has both `@x402/fetch` (scoped stub) and `x402-fetch` (real, v1.1.0). This server uses `x402-fetch` (non-scoped).
**How to avoid:** If the README mentions x402-fetch at all, call this out explicitly: "use `x402-fetch` (not `@x402/fetch`)".

### Pitfall 5: Wallet setup details belong in Phase 3 (brand site)
**What goes wrong:** README becomes too long trying to document wallet creation, USDC funding, Base network — areas better suited for dedicated docs pages.
**Why it happens:** Temptation to be comprehensive.
**How to avoid:** Keep wallet section in README brief (2-3 sentences). Link to the brand site docs (Phase 3). Placeholder link is fine for v1.0.

## Code Examples

### Complete README Tool Table (from src/index.ts)
```markdown
| Tool | Description | Price |
|------|-------------|-------|
| `x402_network_info` | List all APIs with pricing and health status | Free |
| `x402_screenshot` | Capture any URL as a base64 image | $0.01 / capture |
| `x402_pdf_extract` | Extract text from a PDF via URL | $0.01 / extraction |
| `x402_sentiment` | Real-time sentiment analysis for a crypto coin | $0.01 / query |
| `x402_market_overview` | Broad crypto market sentiment overview | $0.05 / query |
| `x402_intelligence` | Multi-source crypto intelligence (CoinGecko, DeFiLlama, news, GitHub) | $0.10 / query |
```

### Free Mode Limitations (from src/index.ts)
- Screenshots: limited to `example.com`, `example.org`, `httpbin.org`
- PDF extraction: first 3 pages only
- Sentiment/intelligence: mock data with real market structure

### .gitignore Change Required
```diff
-# Build output
-dist/
+# Build output — dist/ intentionally committed for npx github: install
+# dist/
```

### GitHub CLI Workflow
```bash
# 1. Rebuild dist to ensure current
npm run build

# 2. Commit dist/
git add dist/
git commit -m "build: commit dist for npx github: install"

# 3. Create public GitHub repo and push
gh repo create x402-mcp-server --public --source=. --remote=origin --push
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE transport for MCP | stdio transport (via npx) | MCP spec v1.0 | npx stdio is now the standard for local MCP servers |
| npm publish for distribution | GitHub direct install | v1.0 decision | No npm account needed; `npx -y github:user/repo` works immediately |
| npm version badge | shields.io GitHub badge | v1.0 (pre-publish) | GitHub badges available without registry listing |

**Deprecated/outdated:**
- `"command": "node", "args": ["/path/to/dist/index.js"]` in MCP configs: Pre-publish local path approach — replaced by npx github: install

## Open Questions

1. **Should `dist/index.d.ts` be committed alongside `dist/index.js`?**
   - What we know: `.d.ts` type declarations are not needed for runtime. `bin` only executes `dist/index.js`. Type declarations are useful if someone imports the package programmatically.
   - What's unclear: Whether committing `.d.ts` adds meaningful value for an MCP server (not typically imported as a library).
   - Recommendation: Commit it alongside `dist/index.js` — trivially small, no harm, and keeps `files` whitelist consistent.

2. **Env var doc approach: `.env` file or inline?**
   - What we know: CONTEXT.md says "reference .env file, not inline". But MCP config JSON files don't auto-load `.env` files. The env key in mcpServers passes vars to the subprocess.
   - What's unclear: Did the user mean "explain they can put the key in a `.env` file and load it into their shell" or "reference a path to a .env file"?
   - Recommendation: Show the actual key value placeholder in the MCP config (that's how all 4 clients work). Add a note: "Never commit your private key. Store it in your system environment or a local `.env` file loaded by your shell." This honors the spirit of the constraint without implying an auto-load mechanism that doesn't exist.

3. **Brand site URL for wallet setup link**
   - What we know: Brand site is Phase 3; no URL exists yet.
   - What's unclear: Whether to use a placeholder URL or omit the link entirely.
   - Recommendation: Use a placeholder comment in README (`<!-- TODO Phase 3: update link -->`) or write "See the [x402 Network docs](#) for wallet setup" with a `#` href. Update in Phase 3.

## Sources

### Primary (HIGH confidence)
- Direct inspection of `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — all 6 tool names, descriptions, prices, free mode limits
- Direct inspection of `/Users/jameswisdom/projects/x402-mcp-server/.gitignore` — confirmed `dist/` excluded
- Direct inspection of `dist/index.js` head — confirmed shebang present
- `gh auth status` — confirmed authenticated as `jameswilliamwisdom`, scope includes `repo`
- `gh repo list jameswilliamwisdom` — confirmed `x402-mcp-server` does not yet exist
- Official Claude Code MCP docs (code.claude.com/docs/en/mcp) — Claude Code MCP config format, `claude mcp add` CLI syntax, scopes
- shields.io official badge endpoints — GitHub license, stars badge URL format

### Secondary (MEDIUM confidence)
- [MCP Setup Guide for Claude Desktop, Cursor, Windsurf](https://help.yourgpt.ai/article/mcp-setup-guide-for-claude-desktop-cursor-and-windsurf-1789) — config file locations for all 3 clients, verified consistent with Windsurf official docs
- [Windsurf Cascade MCP docs](https://docs.windsurf.com/windsurf/cascade/mcp) — Windsurf mcp_config.json format and location

### Tertiary (LOW confidence)
- [npm/cli issue #3692](https://github.com/npm/cli/issues/3692) (open, Feb 2026) — prepare + bin file deletion on global git install
- [npm/cli issue #8440](https://github.com/npm/cli/issues/8440) (July 2025) — devDependencies unavailable during prepare for git deps
- Multiple npm/cli issues #1287, #1229, #1390, #1865 — prepare script unreliability on git deps (converging evidence from multiple sources raises collective confidence to MEDIUM-HIGH)
- [GitHub Docs: Adding locally hosted code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github) — git remote add + push workflow

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tools confirmed via direct system inspection (gh, git, npm all present and working)
- Architecture (dist/ commit requirement): HIGH — verified via .gitignore inspection + converging evidence from multiple npm/cli bug reports
- MCP config formats: HIGH — verified against official Claude Code docs + Windsurf docs
- README structure: MEDIUM — based on conventions and constraints, no single authoritative source
- Pitfalls: HIGH — dist/ issue is definitively confirmed; npx -y is documented in MCP context; others from src inspection

**Research date:** 2026-03-10
**Valid until:** 2026-06-10 (stable domain — npm, GitHub, MCP config formats unlikely to change in 90 days)
