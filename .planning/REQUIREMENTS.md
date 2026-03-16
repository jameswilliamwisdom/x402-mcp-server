# Requirements: Bismuth (x402 API Network)

**Defined:** 2026-03-16
**Core Value:** AI agents can discover and pay for useful APIs with zero integration friction — one npm install, one env var, automatic micropayments.

## v2.0 Requirements

Requirements for v2.0 Bismuth Launch. Each maps to roadmap phases.

### Brand & Domain

- [x] **BRAND-01**: Brand site content rewritten from "x402 API Network" to "Bismuth"
- [x] **BRAND-02**: Site deployed to `usebismuth.com` with HTTPS via Cloudflare Tunnel
- [x] **BRAND-03**: "No API key — pay per call with USDC" messaging prominent on every reference page
- [x] **BRAND-04**: Free test endpoint URL shown prominently above paid endpoint on each docs page

### Documentation

- [ ] **DOCS-01**: API reference page for Web Scraping API with parameter table, curl + MCP tool call examples, error codes
- [ ] **DOCS-02**: API reference page for File Conversion API with parameter table, curl + MCP tool call examples, error codes
- [ ] **DOCS-03**: API reference page for Web Search API with parameter table, curl + MCP tool call examples, error codes
- [ ] **DOCS-04**: API reference page for Email Sending API with parameter table, curl + MCP tool call examples, error codes
- [ ] **DOCS-05**: API reference page for Audio Transcription API with parameter table, curl + MCP tool call examples, error codes

### Email Enhancements

- [ ] **EMAIL-01**: User can send email with CC recipients via x402_send_email tool
- [ ] **EMAIL-02**: User can send email with BCC recipients via x402_send_email tool
- [ ] **EMAIL-03**: User can send email with base64 file attachments (25MB pre-encoding cap)
- [ ] **EMAIL-04**: Attachment size validated before encoding — reject over 25MB with clear error

### Document Conversion

- [ ] **CONV-01**: User can convert DOCX to PDF via x402_convert_file tool (type: "docx")
- [ ] **CONV-02**: DOCX conversion preserves text, headings, tables, and images (semantic fidelity)
- [ ] **CONV-03**: Conversion API docs explicitly note "content-document conversion" — not layout-preserving

### Shallow Crawl

- [ ] **CRAWL-01**: User can crawl a site via new x402_crawl_site MCP tool (POST /crawl endpoint)
- [ ] **CRAWL-02**: Crawl respects max_pages parameter (default 10, max 15) and max_depth (default 2, max 5)
- [ ] **CRAWL-03**: Crawl returns per-page extraction results in same schema as /scrape
- [ ] **CRAWL-04**: All discovered URLs pass SSRF validation before being fetched (not just entry URL)
- [ ] **CRAWL-05**: Crawl supports include/exclude path filters (e.g., `/blog/*`)
- [ ] **CRAWL-06**: Crawl response includes metadata: pages_requested, pages_crawled, pages_skipped, reasons_skipped
- [ ] **CRAWL-07**: Crawl handles partial success — returns results for pages crawled even if some fail
- [ ] **CRAWL-08**: Free test endpoint at GET /crawl/test returns fixture data

### MCP Server

- [ ] **MCP-01**: x402_crawl_site tool registered in src/index.ts with Zod schema
- [ ] **MCP-02**: x402_send_email Zod schema updated to accept cc, bcc, attachments
- [ ] **MCP-03**: x402_convert_file Zod schema updated to accept type: "docx"
- [ ] **MCP-04**: Package version bumped to 2.0.0, published to npm
- [ ] **MCP-05**: README updated with all 12 tools and Bismuth branding

## Future Requirements

Deferred to v2.x or later. Tracked but not in current roadmap.

### Crawl Enhancements

- **CRAWL-F01**: Async job pattern for crawl (POST returns job_id, GET polls status) — enables >15 page crawls
- **CRAWL-F02**: robots.txt respect (default on) + sitemap discovery
- **CRAWL-F03**: Crawl URL normalization (strip utm_* params before dedup)

### Email Enhancements

- **EMAIL-F01**: Inline images (cid: attachments) for branded transactional email

### Documentation

- **DOCS-F01**: Interactive API playground — live request/response testing in docs
- **DOCS-F02**: Getting Started narrative guide for new users

### Conversion

- **CONV-F01**: LibreOffice-based DOCX→PDF for layout-preserving conversion (separate service, +300MB Docker)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Developer platform / marketplace | Future milestone |
| Third-party API hosting | Future milestone |
| User accounts / dashboard | Not this project |
| Speaker diarization | Requires separate model |
| Streaming transcription | Breaks stateless model |
| npm package rename to bismuth-* | x402 is the protocol, package stays x402-mcp-server |
| Mobile app | Not planned |
| Attachment URL fetching | SSRF risk — accept base64 only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BRAND-01 | Phase 11 | Complete |
| BRAND-02 | Phase 11 | Complete |
| BRAND-03 | Phase 11 | Complete |
| BRAND-04 | Phase 11 | Complete |
| DOCS-01 | Phase 12 | Pending |
| DOCS-02 | Phase 12 | Pending |
| DOCS-03 | Phase 12 | Pending |
| DOCS-04 | Phase 12 | Pending |
| DOCS-05 | Phase 12 | Pending |
| EMAIL-01 | Phase 13 | Pending |
| EMAIL-02 | Phase 13 | Pending |
| EMAIL-03 | Phase 13 | Pending |
| EMAIL-04 | Phase 13 | Pending |
| CONV-01 | Phase 14 | Pending |
| CONV-02 | Phase 14 | Pending |
| CONV-03 | Phase 14 | Pending |
| CRAWL-01 | Phase 15 | Pending |
| CRAWL-02 | Phase 15 | Pending |
| CRAWL-03 | Phase 15 | Pending |
| CRAWL-04 | Phase 15 | Pending |
| CRAWL-05 | Phase 15 | Pending |
| CRAWL-06 | Phase 15 | Pending |
| CRAWL-07 | Phase 15 | Pending |
| CRAWL-08 | Phase 15 | Pending |
| MCP-01 | Phase 16 | Pending |
| MCP-02 | Phase 16 | Pending |
| MCP-03 | Phase 16 | Pending |
| MCP-04 | Phase 16 | Pending |
| MCP-05 | Phase 16 | Pending |

**Coverage:**
- v2.0 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 — traceability complete, all 29 requirements mapped to phases 11-16*
