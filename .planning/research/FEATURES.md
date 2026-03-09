# Feature Research

**Domain:** npm MCP server package publishing + developer-facing brand/docs site (Astro)
**Researched:** 2026-03-09
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

#### npm Package

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Installable via `npx` or global npm install | Standard CLI/MCP server distribution method; every well-known MCP server ships this way | LOW | Requires `bin` field + shebang in entry file; `dist/index.js` already in `bin` but needs `#!/usr/bin/env node` |
| Explicit `files` whitelist in package.json | Developers expect clean packages — no test fixtures, planning dirs, source maps unless requested | LOW | Must exclude `.planning/`, `src/`, `.env*`, `openapi/` etc.; only ship `dist/`, `README.md`, `LICENSE` |
| Published README on npm page | npm.js renders the README; it's the primary discovery surface for the package | LOW | README already exists; needs `npx`-style install snippet since that's what users will run post-publish |
| Semantic versioning + git tags | Developers depend on version pinning; `latest` tag must be intentional | LOW | Start at `1.0.0`, tag `v1.0.0` in git before `npm publish` |
| `engines` field specifying Node version | MCP servers run as subprocesses; agents and users need to know the runtime requirement | LOW | Add `"engines": {"node": ">=18"}` — viem and x402-fetch both require 18+ |
| Working `npx x402-mcp-server` invocation | The canonical zero-install MCP server launch pattern | LOW | Needs `#!/usr/bin/env node` shebang + `dist/index.js` must be executable-compatible |
| `.npmignore` or `files` field (not both) | Prevents accidental secret/source leakage | LOW | Use `files` in package.json — more explicit and version-controlled |
| MIT or permissive license file | Developers won't adopt packages without a license; `LICENSE` file must exist | LOW | Already declared MIT in package.json; just needs the actual `LICENSE` file |
| Minimal peer dependencies documented | Users need to know what they must provide (Node, wallet, Claude config) | LOW | README "Requirements" section; not actual npm peerDeps since this is a CLI not a library |

#### Brand/Docs Site

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hero section with one-sentence value prop | Developer landing pages open with the pitch; "what is this" answered in 5 seconds | LOW | "Pay-per-use APIs for AI agents, zero integration friction" |
| Tool listing with names, descriptions, and prices | Developers evaluate fit before installing; pricing transparency is non-negotiable for pay-per-use | LOW | Table mirrors the README tools table; pull from a single source of truth if possible |
| Getting Started guide | Without this, developers stall at the wallet/config step | MEDIUM | Step-by-step: install → add to Claude config → set env var → first tool call; free mode path too |
| API reference for all endpoints | Developers building on top of the APIs directly (not just via MCP) need endpoint docs | MEDIUM | OpenAPI specs exist in `openapi/` — render or link these |
| Copy-pasteable config snippets | Developer docs without code blocks feel broken; Claude config JSON must be copy-pasteable | LOW | Already in README; replicate in docs site with proper syntax highlighting |
| Mobile-responsive layout | Technical developers use phones less but it's still expected; Google will rank it poorly if missing | LOW | Astro + Tailwind handles this trivially |
| Dark mode | Developer tooling audiences overwhelmingly prefer dark mode; light-only feels dated | LOW | Astro + Tailwind CSS variables; can ship both, default dark |
| Fast load time / static output | A brand site that's slow undermines the credibility of a performance-focused infrastructure product | LOW | Astro static output is inherently fast; no JS required for content pages |
| Favicon and basic OG/meta tags | Twitter/X and Slack unfurl previews; missing OG image looks unprofessional when shared | LOW | 1 OG image, title, description meta tags; Astro SEO component handles this |

---

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

#### npm Package

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Free test mode with no wallet required | Lowers adoption barrier dramatically; most MCP servers require full setup immediately | LOW | Already implemented — just needs prominent documentation placement |
| Single env var setup (`X402_PRIVATE_KEY`) | Developer ergonomics; competing payment-enabled packages have multi-step key/config flows | LOW | Already implemented; emphasize it as a design decision, not an accident |
| Payment safety cap hard-coded into the package | Agents calling expensive tools in loops is a real concern; $0.10 cap as a trust signal | LOW | Already implemented at $0.10; mention in README and docs site as a trust feature |
| Network info tool (`x402_network_info`) | Self-describing APIs let agents discover what they can do without reading docs | LOW | Already implemented; position as part of the agent-native design philosophy |

#### Brand/Docs Site

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live pricing display (hardcoded, not dynamic) | Makes the pay-per-use model concrete and trustworthy; most MCP docs hide pricing | LOW | Static table is fine; no need to fetch live prices unless they change |
| "How x402 works" visual explainer | x402 is not widely known; a simple sequence diagram (request → 402 → payment → response) makes it click | MEDIUM | ASCII diagram in code block is acceptable; a real SVG is better; don't block launch on it |
| Free vs. paid comparison table | Developers want to evaluate before committing a wallet; explicit free tier documentation converts better | LOW | One table, four columns: tool, free behavior, paid behavior, price |
| Agent-native framing throughout | Position this as infrastructure for agents, not just another developer tool; language matters | LOW | Use "your agent" not "your app"; "agent-callable" not "API calls" |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| API key / account system on brand site | Seems like a natural onboarding step; common in developer platforms | Out of scope for this milestone; adds auth complexity, database, email flows, security surface | Link to x402 wallet setup guide instead; private key is the "account" |
| Dynamic API status page with live uptime | Transparency is good; developers want to know if APIs are up | Requires polling Railway endpoints from the frontend or a monitoring service; adds runtime dependency and maintenance | Static "current status" note in docs; link to Railway dashboard or add uptime badge later |
| Interactive API playground in the browser | Try-before-you-buy is compelling | Requires running the MCP server in a browser context (impossible for stdio transport); or a separate backend proxy | Screenshot of a Claude session using the tools; GIF or video demo |
| Blog / changelog on the brand site | Common developer site pattern | Content maintenance burden; CMS or markdown pipeline adds complexity; gets stale fast | GitHub releases + a `CHANGELOG.md` in the repo; link from site footer |
| npm install size badge / bundle analysis | Developers care about install size | This is a CLI/server, not a library — install size is irrelevant to the use case | Focus on startup time if anything (stdio MCP servers should start fast) |
| Automated npm publish from CI | Sounds like good hygiene | Adds CI secrets, requires GitHub Actions setup, creates publish-on-push risk | Manual `npm publish` for v1.0; add CI publish after the workflow is understood |

---

## Feature Dependencies

```
[npm package installable via npx]
    └──requires──> [shebang in dist/index.js]
    └──requires──> [files whitelist in package.json]
    └──requires──> [LICENSE file]

[Getting Started guide on site]
    └──requires──> [package published to npm] (can't give real install command before publish)

[Free vs. paid comparison table]
    └──enhances──> [Getting Started guide] (explains free mode before asking for wallet)

[API reference on site]
    └──can use──> [openapi/ specs already in repo]

[OG/meta tags]
    └──enhances──> [brand site] (not blocking, add before launch)

["How x402 works" explainer]
    └──enhances──> [hero section] (context for the value prop)
```

### Dependency Notes

- **npm publish requires files whitelist:** Without an explicit `files` field or `.npmignore`, `npm publish` will ship `.planning/`, `src/`, `openapi/` and potentially expose internal planning files. Must be resolved before `npm publish`.
- **Getting Started requires npm publish:** The install command (`npm install -g x402-mcp-server` or `npx x402-mcp-server`) only works after the package exists on the registry. Brand site launch should follow npm publish by at least minutes.
- **Free vs. paid table enhances Getting Started:** Developers who don't have a wallet yet need to see the free path immediately; this reduces drop-off in the guide.
- **API reference can consume existing OpenAPI specs:** The `openapi/` directory exists; Astro can render these as documentation pages or link to the raw JSON. No new work required to have API docs.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

**npm package:**
- [ ] `#!/usr/bin/env node` shebang in `dist/index.js` (or source `index.ts`) — required for `npx` invocation
- [ ] `files` whitelist in `package.json` — required before publish; prevents source/secrets leakage
- [ ] `LICENSE` file (MIT) — required; npm warns without it
- [ ] `engines` field in `package.json` — sets Node 18+ expectation
- [ ] Updated README with `npx`-style install instructions and Claude config snippet referencing the npm package (not a local path)
- [ ] `npm publish` with `--dry-run` verification first

**Brand site:**
- [ ] Hero with one-sentence value prop — why this exists
- [ ] Tool listing table with prices — what you can do and what it costs
- [ ] Getting Started guide — install → configure → free mode → paid mode
- [ ] Free vs. paid comparison table — lowers wallet barrier
- [ ] Copy-pasteable Claude config JSON — removes the most common friction point
- [ ] Basic OG/meta tags — for link sharing
- [ ] Deployed to home server and accessible via domain

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] "How x402 works" sequence diagram — add when there's evidence developers are confused by the payment mechanism
- [ ] API reference pages from OpenAPI specs — add when direct API consumers appear (vs. MCP-only users)
- [ ] GitHub release + CHANGELOG — add when cutting v1.1 or first patch
- [ ] Uptime / status indicator — add when Railway reliability becomes a concern users raise

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Developer dashboard / account system — Phase 3 per PROJECT.md; needs product validation first
- [ ] Interactive API playground — requires significant backend infrastructure; defer until there's demand signal
- [ ] CI/CD npm publish pipeline — add after manual publish workflow is stable and well-understood
- [ ] Third-party API onboarding — Phase 3 per PROJECT.md

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| files whitelist in package.json | HIGH | LOW | P1 |
| Shebang in entry file | HIGH | LOW | P1 |
| LICENSE file | HIGH | LOW | P1 |
| engines field | MEDIUM | LOW | P1 |
| Updated README (npm install instructions) | HIGH | LOW | P1 |
| npm publish | HIGH | LOW | P1 |
| Hero + value prop | HIGH | LOW | P1 |
| Tool listing with prices | HIGH | LOW | P1 |
| Getting Started guide | HIGH | MEDIUM | P1 |
| Free vs. paid comparison table | HIGH | LOW | P1 |
| Copy-pasteable config snippets | HIGH | LOW | P1 |
| OG/meta tags | MEDIUM | LOW | P1 |
| Dark mode + responsive layout | MEDIUM | LOW | P1 |
| "How x402 works" explainer | MEDIUM | MEDIUM | P2 |
| API reference from OpenAPI specs | MEDIUM | MEDIUM | P2 |
| Uptime/status indicator | LOW | MEDIUM | P3 |
| Blog / changelog on site | LOW | MEDIUM | P3 |
| Interactive playground | MEDIUM | HIGH | P3 |
| CI/CD npm publish | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Prominent MCP servers (e.g., Brave Search, Filesystem) | Other pay-per-use APIs (e.g., Firecrawl MCP) | Our Approach |
|---------|--------------|--------------|--------------|
| Installation | `npx @modelcontextprotocol/server-brave-search` — npx, scoped package | npm install, documented API key env var | Same pattern; unscoped `x402-mcp-server` or consider scoping later |
| Auth setup | Single API key env var | Single API key env var | Single private key env var — same ergonomics, different mechanism (wallet vs. API key) |
| Free tier | None — all tools require API key | None or rate-limited | Full free test mode with meaningful results — differentiator |
| Pricing transparency | Not applicable (API key = subscription) | Pricing on their website, not in the MCP tools | Pricing surfaced both in the `x402_network_info` tool AND on the brand site — stronger trust signal |
| Docs site | GitHub README only (most servers) | Dedicated docs site with guides | Dedicated Astro site — positions x402 as infrastructure, not just a package |
| Self-describing | No — tools don't describe costs | No | Yes — `x402_network_info` returns live API status and pricing to the agent itself |

---

## Sources

- Existing x402 MCP Server codebase (`/Users/jameswisdom/projects/x402-mcp-server/`)
- PROJECT.md milestone requirements and constraints
- MCP server ecosystem conventions: @modelcontextprotocol/server-* packages on npm
- npm publishing best practices: `files` field, `engines`, shebang requirements for CLI packages
- Astro static site capabilities and developer docs site patterns (Starlight, vanilla Astro)
- x402 protocol and pay-per-use API patterns

---
*Feature research for: npm MCP server package publishing + Astro brand/docs site*
*Researched: 2026-03-09*
