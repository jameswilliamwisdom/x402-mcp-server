# Milestones

## v1.0 npm Publish + Brand Site (Shipped: 2026-03-12)

**Phases completed:** 4 phases, 9 plans
**Timeline:** 4 days (2026-03-09 to 2026-03-12)
**Commits:** 39 | **Files:** 68 changed | **Lines:** +15,974

**Key accomplishments:**
- Hardened npm package with `files` whitelist, Zod input validation, and shebang preservation — `x402-mcp-server@1.0.0` published to npm
- Comprehensive README covering 6 tools, 4 MCP clients, pricing table, and free/paid modes
- Astro + Starlight brand site with custom landing page, pricing page, and full developer docs (Getting Started, API Reference, Wallet Setup)
- Deployed to home server (nginx on port 8888, macOS Monterey) with automated deploy script and 9 smoke tests passing

**Archives:**
- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---

## v1.1 Universal Utility APIs (Shipped: 2026-03-15)

**Phases completed:** 6 phases (5-10), 12 plans
**Timeline:** 4 days (2026-03-12 to 2026-03-15)
**Requirements:** 29/29 satisfied

**Key accomplishments:**
- Web scraping API with Playwright JS rendering, trafilatura extraction, dual-layer SSRF protection — deployed to Railway at $0.02/request
- File conversion API unifying image resize (Pillow), CSV→JSON, and HTML→PDF (WeasyPrint) under a single discriminated union endpoint — deployed to Railway at $0.02/request
- Web search API wrapping Tavily with per-wallet rate limiting and domain filtering — deployed to Railway at $0.01/query
- Email sending API with Resend SDK, per-wallet + per-domain rate limiting, and PII-safe logging — deployed to Railway at $0.01/send
- Audio transcription API with faster-whisper small/int8 on home Mac server, Cloudflare Tunnel public access, launchd persistence — $0.05/transcription
- MCP server expanded to 11 tools across 8 APIs, published as `x402-mcp-server@1.1.0` on npm with all free test endpoints

**Archives:**
- [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)
- [v1.1-MILESTONE-AUDIT.md](milestones/v1.1-MILESTONE-AUDIT.md)

---


## v2.0 Bismuth Launch (Shipped: 2026-04-06)

**Phases completed:** 6 phases (11-16), 11 plans
**Timeline:** 21 days (2026-03-16 to 2026-04-06)
**Requirements:** 29/29 satisfied
**Commits:** 41 | **Files:** 55 changed | **Lines:** +10,170

**Key accomplishments:**
- Rebranded to Bismuth — site content, usebismuth.com domain, Cloudflare Tunnel HTTPS, public deployment with zero browser security warnings
- Complete API documentation for all 5 utility APIs in Starlight with parameter tables, curl + MCP examples, error codes, and free test endpoint links
- Email API extended with CC/BCC recipients and base64 file attachments (25MB cap) with decoded-byte size validation and domain rate limiting across all recipients
- DOCX-to-PDF conversion via mammoth + WeasyPrint pipeline — semantic fidelity, zero Docker size cost
- Shallow site crawl: BFS with 15-page sync cap, include/exclude path filters, SSRF validation on every discovered URL, partial results on per-page failure
- Published x402-mcp-server@2.0.0 to npm — 12 tools across 8 APIs, Bismuth branding, test suite with 35 tests added post-publish

**Archives:**
- [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
- [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

