# Roadmap: x402 API Network — v1.0 Publish + Brand

**Milestone:** v1.0 — npm Publish + Brand Site
**Created:** 2026-03-09
**Status:** Planning

## Phase Overview

| Phase | Name | Requirements | Status |
|-------|------|-------------|--------|
| 1 | Package Hardening + Input Validation | Complete    | 2026-03-09 |
| 2 | npm Publish | NPM-01..02 | Pending |
| 3 | Brand Site Build | SITE-01..04, DOCS-01..04, DEPLOY-01 | Pending |
| 4 | Deployment | DEPLOY-02 | Pending |

---

## Phase 1: Package Hardening + Input Validation

**Goal:** Lock down the npm package so it is safe to publish publicly. The `files` whitelist is the highest-risk item in the project — a publish without it could expose `X402_PRIVATE_KEY` to the public registry. All hardening and security changes that affect published code land here, before any public artifact is created.

**Requirements covered:** PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, PKG-06, VAL-01, VAL-02

**Plans:** 2/2 plans complete

Plans:
- [x] 01-01-PLAN.md — Package hardening: files whitelist, lifecycle scripts, engines, LICENSE, .gitignore, publint + zod deps (completed 2026-03-09)
- [x] 01-02-PLAN.md — Input validation: Zod schema tightening on coin/url/pdf_url params + full build & package verification (completed 2026-03-09)

### Success Criteria

1. `npm pack --dry-run` output contains no `.env`, `src/`, `.planning/`, or any file outside `dist/`, `README.md`, `LICENSE`, `package.json`
2. `head -1 dist/index.js` returns `#!/usr/bin/env node` after every `npm run build`
3. `npx publint` exits 0 with no errors or warnings
4. A `coin` value of `"; DROP TABLE"` passed to the crypto sentiment tool is rejected by Zod before any network call is made
5. A non-URL string passed to a `url` or `pdf_url` parameter is rejected by Zod with a validation error

---

## Phase 2: npm Publish

**Goal:** Prepare the package for GitHub direct install distribution, write a comprehensive README with all MCP client configs, create a public GitHub repo, and verify end-to-end install via `npx -y github:jameswilliamwisdom/x402-mcp-server`. npm registry publish deferred until account issues resolved.

**Requirements covered:** NPM-01, NPM-02

**Prerequisite:** Phase 1 complete

**Plans:** 1 plan

Plans:
- [ ] 02-01-PLAN.md — GitHub distribution: commit dist/, comprehensive README, create public repo, verify npx install

### Success Criteria

1. `npx -y github:jameswilliamwisdom/x402-mcp-server` launches the MCP server from any directory without errors
2. README on GitHub shows free mode first, all 4 client configs (Claude Desktop, Claude Code, Cursor, Windsurf), tools table with pricing, shields.io badges
3. All `npx` references use the `-y` flag (verified by grep)
4. GitHub repo is public at `github.com/jameswilliamwisdom/x402-mcp-server`

---

## Phase 3: Brand Site Build

**Goal:** Scaffold and populate the Astro + Starlight brand site in `site/` with all marketing and documentation content. The site lives in the same repo but has its own `package.json` so Astro never enters the npm bundle. Content is written against the live npm package (correct version numbers, real install commands).

**Requirements covered:** SITE-01, SITE-02, SITE-03, SITE-04, DOCS-01, DOCS-02, DOCS-03, DOCS-04, DEPLOY-01

**Prerequisite:** Phase 2 complete

### Tasks

**Scaffold**
1. Scaffold Astro + Starlight in `site/`: `npm create astro@latest site -- --template starlight`
2. Set `output: 'static'` explicitly in `site/astro.config.mjs` (do not rely on implicit default)
3. Set `site:` field in `astro.config.mjs` to the home server address once confirmed
4. Run `npm run build` inside `site/` and verify `site/dist/` contains `index.html` (not a `server/` directory)

**Marketing pages (SITE-01..04)**
5. Build hero section in `site/src/pages/index.astro`:
   - One-liner pitch: "Pay-per-use APIs for AI agents. One npm install, automatic USDC micropayments on Base."
   - Primary CTA linking to Getting Started guide
   - Value proposition bullets (free test mode, single env var, $0.10/request cap)
6. Build pricing table component listing all 6 MCP tools with names, descriptions, and per-call USDC cost
7. Build "How it works" section explaining the x402 payment flow (agent calls tool → MCP server intercepts 402 → `x402-fetch` pays USDC → API responds)
8. Add OG meta tags to `site/src/layouts/` or directly in page `<head>`: `og:title`, `og:description`, `og:image`, `twitter:card`
9. Create OG image asset in `site/public/`

**Documentation pages (DOCS-01..04)**
10. Write Getting Started guide at `site/src/content/docs/getting-started.mdx`:
    - Free mode path: install → add to Claude config (no wallet) → list available tools → call a free tool
    - Paid mode path: fund Base wallet with USDC → set `X402_PRIVATE_KEY` env var → call paid tool
    - Note the `@x402/fetch` vs `x402-fetch` distinction (common mistake)
11. Write API reference at `site/src/content/docs/api-reference.mdx`:
    - All 6 MCP tools with parameter tables, return schemas, and usage examples
    - Free vs. paid column for each tool
12. Write copy-pasteable Claude Desktop config block in Getting Started (or standalone page):
    - JSON with `command: "npx"`, `args: ["-y", "x402-mcp-server"]`, `env` object
    - Must use `-y` flag
13. Write wallet setup guide at `site/src/content/docs/wallet-setup.mdx`:
    - Add Base network to MetaMask
    - Bridge or buy USDC on Base
    - Export private key safely (env var, not hardcoded)

**Validation**
14. Grep all docs for `npx x402-mcp-server` without `-y` — fix any occurrences
15. Verify pricing table matches values in `src/index.ts` (add sync comments to both files)
16. Run `npm run build` inside `site/` — zero errors, `site/dist/index.html` exists

### Success Criteria

1. A developer landing on the site's home page can read the one-liner pitch, understand the payment model, and reach the Getting Started guide within two clicks
2. The pricing table on the site matches the per-call costs declared in `src/index.ts` exactly
3. Pasting the Claude Desktop config JSON from the docs page into `~/Library/Application Support/Claude/claude_desktop_config.json` and restarting Claude Desktop results in the 6 x402 tools appearing in the tool list
4. `npm run build` inside `site/` exits 0 and produces `site/dist/index.html` with no `server/` directory present
5. All `npx` references in site content use the `-y` flag (verified by grep)

---

## Phase 4: Deployment

**Goal:** Deploy the built static site to the home server and verify it is publicly accessible. This is the final verification step — confirms static output, nginx configuration, and routing are all correct before calling the milestone done.

**Requirements covered:** DEPLOY-02

**Prerequisite:** Phase 3 complete (`site/dist/` built and verified)

### Tasks

1. Confirm target path on home server (e.g., `/var/www/x402-network/`)
2. Run `npm run build` inside `site/` for a clean production build
3. rsync built output to home server: `rsync -av --delete site/dist/ user@homeserver:/var/www/x402-network/`
4. Configure nginx `server` block:
   - `root /var/www/x402-network;`
   - `index index.html;`
   - `try_files $uri $uri/ /index.html;`
   - Confirm `.planning/` directory is NOT in the web root (it's at repo root, not `site/dist/` — verify with `curl http://server/.planning/` returns 404)
5. Obtain TLS certificate with Let's Encrypt / certbot for the server domain
6. Configure nginx HTTPS redirect (port 80 → 443)
7. Reload nginx: `sudo nginx -t && sudo systemctl reload nginx`
8. Smoke test from an external network:
   - `curl -I https://<domain>/` returns 200
   - `curl -I https://<domain>/.planning/` returns 404
   - `curl -I https://<domain>/docs/getting-started/` returns 200
   - OG meta tags visible in `curl https://<domain>/ | grep og:`

### Success Criteria

1. `curl -I https://<domain>/` from an external network returns HTTP 200 with `Content-Type: text/html`
2. `curl -I https://<domain>/.planning/` returns 404 (planning files not exposed)
3. The Getting Started docs page loads over HTTPS without mixed-content warnings
4. Sharing the site URL in a chat client renders the OG title and description from the meta tags

---

## Sequencing Rationale

- Phase 1 before all: `files` whitelist and input validation are pre-publish blockers with zero dependencies. Resolving them first eliminates the highest-risk action in the project.
- Phase 2 after Phase 1: npm publish requires a hardened package. The brand site cannot reference a real install command until the package exists on npm.
- Phase 3 after Phase 2: All Getting Started and API reference content references the live npm package. Writing docs before publish risks version number drift.
- Phase 4 after Phase 3: Static site must be fully built and verified locally before deploying. A partial or broken deploy creates a worse first impression than no site.
- Marketing pages (SITE-*) and docs pages (DOCS-*) are in the same phase: they share the Astro scaffold and have no sequencing dependency between them.

---

## Requirement Coverage

All 20 v1 requirements are mapped. See `REQUIREMENTS.md` traceability table for phase assignments.

---

*Roadmap created: 2026-03-09*
*Milestone: v1.0 — Publish + Brand*
