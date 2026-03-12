# x402 API Network

## What This Is

Infrastructure for the AI agent economy using the x402 protocol. A unified MCP server that wraps pay-per-use APIs (screenshot capture, PDF extraction, crypto sentiment) as agent-callable tools with automatic USDC micropayment handling on Base. Published to npm as `x402-mcp-server`, with a brand site providing marketing pitch, pricing, and developer documentation.

## Core Value

AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## Current State

**Shipped:** v1.0 (2026-03-12) — npm Publish + Brand Site
- `x402-mcp-server@1.0.0` on npm — `npx -y x402-mcp-server`
- Brand site live at `http://10.0.0.2:8888` (local network, HTTP only)
- 6 MCP tools across 3 APIs, all with free test endpoints
- Full developer docs: Getting Started, API Reference, Wallet Setup

## Requirements

### Validated

- ✓ `files` whitelist, lifecycle scripts, engines, LICENSE, shebang, publint — v1.0
- ✓ Zod input validation on coin/url/pdf_url params — v1.0
- ✓ npm package published as `x402-mcp-server` with comprehensive README — v1.0
- ✓ Brand site with hero, pricing table, how-it-works, OG meta tags — v1.0
- ✓ Developer docs: Getting Started, API Reference, Wallet Setup — v1.0
- ✓ Astro static build, deployed to home server — v1.0

### Active

(None — next milestone not yet scoped)

### Out of Scope

- Developer platform / marketplace — future milestone
- Third-party API hosting — future milestone
- Own L2 chain — far future
- Mobile app — not planned
- User accounts / dashboard — not this project
- Interactive API playground — requires backend proxy

## Context

- **Stack:** TypeScript, @modelcontextprotocol/sdk, viem, x402-fetch
- **Site stack:** Astro 5 + Starlight 0.37.7 (static output, dark-mode-only)
- **APIs:** Railway-hosted Python/FastAPI services with fastapi-x402
- **Wallet:** 0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC (MetaMask, Base network)
- **Token:** USDC on Base
- **Server:** macOS Monterey x86_64 at 10.0.0.2, nginx on port 8888 (AdGuard Home on 80)
- **Package gotcha:** Use `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub)
- **Zod override:** site/package.json pins zod to 3.25.76, @astrojs/sitemap to 3.6.1 (Starlight/Zod 4 conflict)

## Constraints

- **Security:** No private keys or secrets in published package — env var only
- **Package boundary:** Explicit `files` field in package.json to control what ships
- **Input validation:** Coin params need regex validation, URLs need `.url()` validation
- **Hosting:** Brand site must be deployable to home server (static output)
- **Port 80:** AdGuard Home on server — nginx uses port 8888
- **No domain/TLS:** HTTP only for v1, domain + Cloudflare proxy deferred

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Astro + Starlight for brand site | Fast static output, great for content + docs, deploys anywhere | ✓ Good — 1.25s builds, 6 pages, search included |
| Self-host brand site | Control, no recurring costs, existing home server infra | ✓ Good — nginx on home Mac, deploy.sh with smoke tests |
| npm publish before brand site | Establishes the package, brand site references it | ✓ Good — real install commands in docs, no placeholder drift |
| Dark-mode-only Starlight | Brand aesthetics, simpler CSS | ✓ Good — ForceDarkTheme + EmptyComponent pattern |
| Port 8888 for nginx | AdGuard Home occupies port 80 | ✓ Good — no conflict, no sudo needed |
| GitHub distribution first, npm later | npm account access delayed | ✓ Good — unblocked Phase 2, npm published same session |

---
*Last updated: 2026-03-12 after v1.0 milestone*
