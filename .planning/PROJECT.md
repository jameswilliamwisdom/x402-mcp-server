# x402 API Network

## What This Is

Infrastructure for the AI agent economy using the x402 protocol. A unified MCP server that wraps pay-per-use universal utility APIs as agent-callable tools with automatic USDC micropayment handling on Base. The strategic position is "AWS primitives for agents" — stateless, high-frequency, micropayment-optimized utilities that every agent workflow needs regardless of domain.

## Core Value

AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## Current Milestone: v1.1 Universal Utility APIs

**Goal:** Add 5 new APIs to the x402 network, expanding from 3 to 8 backend services and from 6 to ~16 MCP tools. Each API follows the proven pattern: stateless, sub-$0.10, no account required, free test endpoint.

**Target APIs:**
- Web Scraping + Structured Extraction (Playwright + Cheerio, Railway)
- Email Sending (Resend backend, Railway)
- Web Search (search engine TBD — research during planning, Railway)
- File Conversion (doc-to-pdf, image resize, html-to-pdf, csv-to-json, Railway)
- Audio Transcription (MLX Whisper, self-hosted on home Mac server)

## Current State

**Shipped:** v1.0 (2026-03-12) — npm Publish + Brand Site
- `x402-mcp-server@1.0.0` on npm — `npx -y x402-mcp-server`
- Brand site live at `http://10.0.0.2:8888` (local network, HTTP only)
- 6 MCP tools across 3 APIs, all with free test endpoints
- Full developer docs: Getting Started, API Reference, Wallet Setup

## Requirements

### Validated

- ✓ 3 live APIs on Railway (Screenshot, PDF Extraction, Crypto Sentiment) — v1.0
- ✓ MCP server with 6 tools, automatic USDC micropayments — v1.0
- ✓ npm package published as `x402-mcp-server` with comprehensive README — v1.0
- ✓ Brand site with marketing + developer docs, deployed to home server — v1.0
- ✓ Package security: files whitelist, Zod validation, shebang, publint — v1.0

### Active

- [ ] Web scraping API: URL → structured JSON (text, links, metadata, tables)
- [ ] Email sending API: stateless send via Resend (to/from/subject/body)
- [ ] Web search API: query → top N results as structured JSON
- [ ] File conversion API: format-to-format transformations
- [ ] Audio transcription API: audio URL → text transcript (MLX Whisper)
- [ ] MCP server updated with new tools + npm publish v1.1
- [ ] Free test endpoints for all new APIs

### Out of Scope

- Brand site / docs updates — separate milestone after APIs ship
- Developer platform / marketplace — future milestone
- Third-party API hosting — future milestone
- Own L2 chain — far future
- Mobile app — not planned
- User accounts / dashboard — not this project
- Domain / TLS / public access — separate milestone
- Crypto sentiment refactoring — works, leave it alone

## Context

- **Stack:** TypeScript, @modelcontextprotocol/sdk, viem, x402-fetch
- **API pattern:** Python/FastAPI on Railway with fastapi-x402 (proven with screenshot + PDF)
- **Wallet:** 0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC (MetaMask, Base network)
- **Token:** USDC on Base
- **Home server:** macOS Monterey x86_64 at 10.0.0.2 (nginx port 8888, MLX Whisper available)
- **Email backend:** Resend (modern transactional email, generous free tier)
- **Search backend:** TBD — research SerpAPI, Brave, Tavily during planning
- **Package gotcha:** Use `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub)
- **Strategic insight:** Screenshot and PDF are the strongest tools because they're boring universal utilities. Crypto sentiment is the weakest fit (niche). Build more like the first two.

## Constraints

- **Security:** No private keys or secrets in published package — env var only
- **Package boundary:** Explicit `files` field in package.json to control what ships
- **Input validation:** All user-facing params validated with Zod before any network call
- **API pattern:** Same FastAPI + fastapi-x402 pattern for consistency (except transcription)
- **Transcription hosting:** MLX Whisper on home server (10.0.0.2), not Railway — no GPU rental cost
- **Pricing cap:** All requests sub-$0.10 USDC — micropayment positioning

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Astro + Starlight for brand site | Fast static output, great for content + docs | ✓ Good |
| Self-host brand site | Control, no recurring costs | ✓ Good |
| Port 8888 for nginx | AdGuard Home occupies port 80 | ✓ Good |
| "AWS primitives for agents" positioning | Universal utilities > niche crypto tools | — Pending |
| Resend for email sending | Modern, free tier, developer-friendly | — Pending |
| MLX Whisper self-hosted for transcription | No GPU rental cost, hardware already available | — Pending |
| Playwright + Cheerio for web scraping | Full control, no third-party dependency/cost | — Pending |
| APIs + MCP only for v1.1 | Ship backend first, update site/docs in separate milestone | — Pending |

---
*Last updated: 2026-03-12 after v1.1 milestone initialization*
