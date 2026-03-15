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

