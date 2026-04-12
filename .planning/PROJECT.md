# Bismuth (x402 API Network)

## What This Is

Infrastructure for the AI agent economy using the x402 protocol, branded as **Bismuth**. A unified MCP server (`x402-mcp-server@2.0.0` on npm) wrapping 8 pay-per-use utility APIs as 12 agent-callable tools with automatic USDC micropayment handling on Base. The strategic position is "AWS primitives for agents" — stateless, high-frequency, micropayment-optimized utilities that every agent workflow needs regardless of domain.

**Brand:** Bismuth — live at `https://usebismuth.com` — npm package stays `x402-mcp-server` (x402 = protocol)

## Core Value

AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## Current State

**Shipped:** v2.0 Bismuth Launch (2026-04-06)
- `x402-mcp-server@2.0.0` on npm — 12 tools across 8 APIs
- Brand site live at `https://usebismuth.com` with Cloudflare Tunnel HTTPS
- Complete API reference docs for all 5 utility APIs in Starlight
- 5 Railway services + 1 home-server service
- All tools have free test endpoints — no USDC required to try
- Test suite: 35 tests via Vitest + MCP InMemoryTransport

**12 Tools:**
| Tool | API | Price |
|------|-----|-------|
| x402_network_info | — | Free |
| x402_screenshot | Screenshot | $0.01 |
| x402_pdf_extract | PDF | $0.01 |
| x402_sentiment | Sentiment | $0.01 |
| x402_market_overview | Sentiment | $0.05 |
| x402_intelligence | Sentiment | $0.10 |
| x402_send_email | Email | $0.01 |
| x402_scrape_url | Scraping | $0.02 |
| x402_convert_file | Conversion | $0.02 |
| x402_web_search | Search | $0.01 |
| x402_transcribe_audio | Transcription | $0.05 |
| x402_crawl_site | Scraping | $0.10 |

**Production URLs:**
- Screenshot: https://usdc-screenshot-api-production.up.railway.app
- PDF: https://pdf-api-production-cf1e.up.railway.app
- Sentiment: https://crypto-sentiment-api-production-0ff4.up.railway.app
- Email: https://x402-email-api-production.up.railway.app
- Scraping: https://x402-scraping-api-production.up.railway.app
- Conversion: https://x402-conversion-api-production.up.railway.app
- Search: https://x402-search-api-production.up.railway.app
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
- ✓ Bismuth rebrand — site content, usebismuth.com domain, Cloudflare Tunnel HTTPS — v2.0
- ✓ API reference docs for all 5 utility APIs in Starlight — v2.0
- ✓ Email CC/BCC + base64 attachments with decoded-byte size validation — v2.0
- ✓ DOCX-to-PDF via mammoth + WeasyPrint (semantic fidelity) — v2.0
- ✓ Shallow site crawl: BFS, 15-page cap, path filters, per-URL SSRF — v2.0
- ✓ x402-mcp-server@2.0.0 published with 12 tools + Bismuth branding — v2.0

### Active

(None — next milestone not yet defined)

### Out of Scope

- Developer platform / marketplace — future milestone
- Third-party API hosting — future milestone
- Own L2 chain — far future
- Mobile app — not planned
- User accounts / dashboard — not this project
- Speaker diarization — requires separate model
- Real-time streaming transcription — breaks stateless model
- npm package rename to bismuth-* — x402 is the protocol, package stays x402-mcp-server
- Attachment URL fetching — SSRF risk, accept base64 only

## Context

- **Stack:** TypeScript MCP server, Python/FastAPI backends, x402-fetch for payments
- **API pattern:** FastAPI + fastapi-x402 on Railway (4 services) + home server (1 service)
- **Wallet:** 0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC (MetaMask, Base network, USDC)
- **Home server:** macOS Monterey x86_64 at 10.0.0.2, faster-whisper small/int8/CPU, Cloudflare Tunnel
- **Email backend:** Resend with verified sender domain (jameswisdom.ink)
- **Search backend:** Tavily ($0.008/query, AsyncTavilyClient)
- **LOC:** ~3,500 across TypeScript + Python
- **Package:** `x402-fetch` (non-scoped, v1.1.0), not `@x402/fetch` (placeholder stub)
- **Testing:** Vitest, 35 tests, MCP InMemoryTransport for end-to-end tool testing

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
| Resend for email sending | Modern, free tier, developer-friendly | ✓ Good |
| faster-whisper self-hosted for transcription | No GPU rental cost, hardware already available | ✓ Good |
| Playwright + trafilatura for web scraping | Full control, no third-party dependency/cost | ✓ Good |
| Tavily for web search | Best API for agent use, synthesized answers | ✓ Good |
| Cloudflare Tunnel for transcription + site | Zero router config, no exposed home IP | ✓ Good |
| npm passkey auth | iCloud Keychain + --auth-type=web for publish | ✓ Good |
| mammoth + WeasyPrint for DOCX | Zero Docker size cost, semantic fidelity | ✓ Good |
| Sync crawl with 15-page cap | Async job pattern deferred to v2.x | ✓ Good — simple, reliable |
| stdlib BFS for crawl (no crawlee) | No new runtime deps, deque + fnmatch sufficient | ✓ Good |
| Extract helpers.ts for testability | Single-file was untestable | ✓ Good — enabled 35 tests |
| Guard main() with isDirectRun | Allow test imports without stdio auto-connect | ⚠️ Revisit — brittle, use import.meta.url |

## Known Issues (from v2.0 post-ship audit)

- **SSRF**: `z.string().url()` accepts non-HTTP schemes + private IPs — needs safeHttpUrl validator
- **No timeouts**: `apiGet`/`apiPost` have no AbortSignal — hung backends hang the MCP server
- **Private key validation**: `as` cast, no runtime format check
- **Paid mode untested**: zero test coverage on the code path that moves real USDC
- **No CI**: no GitHub Actions pipeline
- **Attachment size unbounded**: Zod accepts gigabyte base64 strings
- **Error body leaks**: raw backend error text forwarded to agent
- **No logging**: payment failures leave no server-side trace

---
*Last updated: 2026-04-12 after v2.0 milestone*
