# x402 API Network

## What This Is

Infrastructure for the AI agent economy using the x402 protocol. A unified MCP server (`x402-mcp-server@1.1.0` on npm) wrapping 8 pay-per-use utility APIs as 11 agent-callable tools with automatic USDC micropayment handling on Base. The strategic position is "AWS primitives for agents" — stateless, high-frequency, micropayment-optimized utilities that every agent workflow needs regardless of domain.

## Core Value

AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## Current State

**Shipped:** v1.1 (2026-03-15) — Universal Utility APIs
- `x402-mcp-server@1.1.0` on npm — 11 tools across 8 APIs
- 5 Railway services: scraping ($0.02), conversion ($0.02), search ($0.01), email ($0.01), + 3 original
- 1 home-server service: transcription ($0.05) at `transcribe.jameswisdom.ink`
- All tools have free test endpoints — no USDC required to try
- Brand site live at `http://10.0.0.2:8888` (local network, HTTP only)

**Production URLs:**
- Scraping: https://x402-scraping-api-production.up.railway.app
- Conversion: https://x402-conversion-api-production.up.railway.app
- Search: https://x402-search-api-production.up.railway.app
- Email: https://x402-email-api-production.up.railway.app
- Transcription: https://transcribe.jameswisdom.ink

## Requirements

### Validated

- ✓ 3 live APIs on Railway (Screenshot, PDF Extraction, Crypto Sentiment) — v1.0
- ✓ MCP server with 6 tools, automatic USDC micropayments — v1.0
- ✓ npm package published as `x402-mcp-server` with comprehensive README — v1.0
- ✓ Brand site with marketing + developer docs, deployed to home server — v1.0
- ✓ Package security: files whitelist, Zod validation, shebang, publint — v1.0
- ✓ Web scraping API: URL → structured JSON with Playwright + trafilatura — v1.1
- ✓ File conversion API: image resize, CSV→JSON, HTML→PDF — v1.1
- ✓ Web search API: Tavily-backed query → ranked results — v1.1
- ✓ Email sending API: Resend-backed transactional email — v1.1
- ✓ Audio transcription API: faster-whisper on home server — v1.1
- ✓ MCP server updated to 11 tools, published as v1.1.0 — v1.1
- ✓ Free test endpoints for all APIs — v1.1

### Active — v2.0 Site Launch & Platform Polish

- Brand site docs updated for all v1.1 APIs (scraping, conversion, search, email, transcription)
- Custom domain with SSL — brand site publicly accessible via HTTPS
- Full site crawl — multi-page scraping capability for scraping API
- Email attachments, CC/BCC — richer email sending
- DOCX→PDF conversion — research lightweight alternatives to LibreOffice

### Out of Scope

- Developer platform / marketplace — future milestone
- Third-party API hosting — future milestone
- Own L2 chain — far future
- Mobile app — not planned
- User accounts / dashboard — not this project
- Speaker diarization — requires separate model
- Real-time streaming transcription — breaks stateless model

## Context

- **Stack:** TypeScript MCP server, Python/FastAPI backends, x402-fetch for payments
- **API pattern:** FastAPI + fastapi-x402 on Railway (4 services) + home server (1 service)
- **Wallet:** 0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC (MetaMask, Base network, USDC)
- **Home server:** macOS Monterey x86_64 at 10.0.0.2, faster-whisper small/int8/CPU, Cloudflare Tunnel
- **Email backend:** Resend with verified sender domain (jameswisdom.ink)
- **Search backend:** Tavily ($0.008/query, AsyncTavilyClient)
- **LOC:** ~3,200 across TypeScript + Python
- **Package:** `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub)

## Constraints

- **Security:** No private keys or secrets in published package — env var only
- **Package boundary:** Explicit `files` field in package.json (5 files published)
- **Input validation:** All user-facing params validated with Zod before any network call
- **API pattern:** Same FastAPI + fastapi-x402 pattern for consistency
- **Pricing cap:** All requests sub-$0.10 USDC — micropayment positioning
- **SSRF:** All URL-accepting services validate resolved IPs against private/loopback ranges

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Astro + Starlight for brand site | Fast static output, great for content + docs | ✓ Good |
| Self-host brand site | Control, no recurring costs | ✓ Good |
| Port 8888 for nginx | AdGuard Home occupies port 80 | ✓ Good |
| "AWS primitives for agents" positioning | Universal utilities > niche crypto tools | ✓ Good — v1.1 validates the pattern |
| Resend for email sending | Modern, free tier, developer-friendly | ✓ Good — clean SDK, SPF/DKIM/DMARC verified |
| faster-whisper self-hosted for transcription | No GPU rental cost, hardware already available | ✓ Good — small/int8 runs well on Intel CPU |
| Playwright + trafilatura for web scraping | Full control, no third-party dependency/cost | ✓ Good — JS rendering + structured extraction |
| Tavily for web search | Best API for agent use, synthesized answers | ✓ Good — $0.008/query, clean results |
| APIs + MCP only for v1.1 | Ship backend first, update site/docs separately | ✓ Good — shipped in 4 days |
| Cloudflare Tunnel for transcription | Zero router config, no exposed home IP | ✓ Good — works with launchd persistence |
| npm passkey auth | iCloud Keychain + --auth-type=web for publish | ✓ Good — replaces TOTP hassle |

---
*Last updated: 2026-03-15 — v2.0 milestone started*
