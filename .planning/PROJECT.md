# x402 API Network

## What This Is

Infrastructure for the AI agent economy using the x402 protocol. A unified MCP server that wraps pay-per-use APIs (screenshot capture, PDF extraction, crypto sentiment) as agent-callable tools with automatic USDC micropayment handling on Base. The "Levi Strauss play" — providing essential tools and services to AI agents rather than speculating on individual cryptocurrencies.

## Core Value

AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## Current Milestone: v1.0 Publish + Brand

**Goal:** Ship the MCP server to npm and launch a brand site that explains the network, shows pricing, and provides developer documentation.

**Target features:**
- npm publish with security hardening
- Astro brand site with marketing pitch + API docs + getting started guide
- Self-hosted on home server

## Requirements

### Validated

- ✓ 3 live APIs on Railway (Screenshot, PDF Extraction, Crypto Sentiment)
- ✓ MCP server wrapping all 3 APIs as agent-callable tools (6 tools)
- ✓ Automatic USDC micropayment handling via x402-fetch + viem
- ✓ Free test endpoints for all APIs (no wallet required)
- ✓ Payment safety cap ($0.10 USDC per request)

### Active

- [ ] npm package published and installable
- [ ] Brand site live with marketing + developer docs
- [ ] API documentation for all endpoints
- [ ] Getting started guide for developers

### Out of Scope

- Developer platform / marketplace — Phase 3
- Third-party API hosting — Phase 3
- Own L2 chain — Phase 4
- Mobile app — not planned
- User accounts / dashboard — not this milestone

## Context

- **Stack:** TypeScript, @modelcontextprotocol/sdk, viem, x402-fetch
- **APIs:** Railway-hosted Python/FastAPI services with fastapi-x402
- **Wallet:** 0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC (MetaMask, Base network)
- **Token:** USDC on Base
- **Brand site stack:** Astro (static site generator)
- **Hosting:** Self-hosted on home server
- **Package gotcha:** Use `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub)

## Constraints

- **Security:** No private keys or secrets in published package — env var only
- **Package boundary:** Explicit `files` field in package.json to control what ships
- **Input validation:** Coin params need regex validation, URLs need `.url()` validation
- **Hosting:** Brand site must be deployable to home server (static output)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Astro for brand site | Fast static output, great for content + docs, deploys anywhere | — Pending |
| Self-host brand site | Control, no recurring costs, existing home server infra | — Pending |
| npm publish before brand site | Establishes the package, brand site references it | — Pending |

---
*Last updated: 2026-03-09 after milestone v1.0 initialization*
