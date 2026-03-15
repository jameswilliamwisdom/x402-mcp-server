# Requirements: x402 API Network

**Defined:** 2026-03-12
**Core Value:** AI agents can discover and pay for useful APIs with zero integration friction

## v1.1 Requirements

Requirements for milestone v1.1 — Universal Utility APIs. Each maps to roadmap phases.

### Web Scraping

- [x] **SCRAPE-01**: Given a URL, return structured JSON with markdown text, extracted links, and page metadata
- [x] **SCRAPE-02**: JS-rendered pages supported via Playwright (not just static HTML)
- [x] **SCRAPE-03**: `wait_for` CSS selector parameter for async SPA content
- [x] **SCRAPE-04**: SSRF protection — server-side IP validation rejects private/loopback ranges
- [x] **SCRAPE-05**: Free test endpoint with fixture data (no live scraping)

### Email Sending

- [x] **EMAIL-01**: Send email with to, subject, plain text body via Resend
- [x] **EMAIL-02**: HTML body support with auto plain-text fallback
- [x] **EMAIL-03**: Verified sender domain with SPF/DKIM/DMARC configured
- [x] **EMAIL-04**: Abuse limits — rate limit per wallet (10 sends/day)
- [x] **EMAIL-05**: Free test endpoint (sandbox mode, no real delivery)

### Web Search

- [x] **SEARCH-01**: Given a query, return top N results (title, URL, snippet) as JSON via Tavily
- [x] **SEARCH-02**: `include_answer` param — synthesized answer with sources
- [x] **SEARCH-03**: `include_domains`/`exclude_domains` for focused research
- [x] **SEARCH-04**: Per-wallet daily query limit to prevent cost spikes
- [x] **SEARCH-05**: Free test endpoint with fixture data

### File Conversion

- [x] **CONV-01**: Image resize/reformat (Pillow) — input URL + target dimensions/format
- [x] **CONV-02**: CSV→JSON conversion (Python stdlib)
- [x] **CONV-03**: HTML→PDF conversion (WeasyPrint)
- [x] **CONV-04**: SSRF protection on file fetch URLs
- [x] **CONV-05**: Free test endpoint with fixture data

### Audio Transcription

- [x] **TRANS-01**: Given an audio URL, return text transcript via faster-whisper on home server
- [x] **TRANS-02**: Auto language detection with detected language in response
- [x] **TRANS-03**: Optional word-level timestamps
- [x] **TRANS-04**: Language hint parameter for known languages
- [x] **TRANS-05**: Size/duration limits (25MB / 10 min) with clear error messages
- [x] **TRANS-06**: Free test endpoint with fixture data

### MCP Server + Publish

- [ ] **MCP-01**: 5 new tools registered in src/index.ts with Zod validation
- [ ] **MCP-02**: npm publish as x402-mcp-server@1.1.0
- [ ] **MCP-03**: x402_network_info tool updated with health checks for all 8 APIs

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### File Conversion — Extended
- **CONV-EXT-01**: DOCX→PDF conversion via LibreOffice headless (deferred — 300MB Docker image)

### Transcription — Extended
- **TRANS-EXT-01**: Speaker diarization (requires separate model)
- **TRANS-EXT-02**: Real-time streaming transcription (WebSocket, breaks stateless model)

### Web Scraping — Extended
- **SCRAPE-EXT-01**: LLM-based structured extraction (schema → structured JSON per Firecrawl pattern)
- **SCRAPE-EXT-02**: Full site crawl (multi-page)

### Email — Extended
- **EMAIL-EXT-01**: File attachments
- **EMAIL-EXT-02**: CC/BCC and multiple recipients

### Infrastructure
- **INFRA-01**: Custom domain with SSL for brand site
- **INFRA-02**: Port forwarding for transcription API public access
- **INFRA-03**: Brand site + docs updated with new APIs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Developer platform / marketplace | Future milestone |
| Third-party API hosting | Future milestone |
| Own L2 chain | Far future |
| Mobile app | Not planned |
| User accounts / dashboard | Not this project |
| Video conversion | FFmpeg bloat, niche use case |
| PDF→editable formats | Use existing pdf_extract tool |
| Cookie/session injection for scraping | Breaks stateless constraint |
| Proxy rotation for scraping | Infrastructure cost + legal complexity |
| Email scheduling | Requires state — breaks stateless model |
| Bulk email sending | Abuse risk too high |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRAPE-01 | 5 | Complete |
| SCRAPE-02 | 5 | Complete |
| SCRAPE-03 | 5 | Complete |
| SCRAPE-04 | 5 | Complete |
| SCRAPE-05 | 5 | Complete |
| EMAIL-01 | 8 | Complete |
| EMAIL-02 | 8 | Complete |
| EMAIL-03 | 8 | Complete |
| EMAIL-04 | 8 | Complete |
| EMAIL-05 | 8 | Complete |
| SEARCH-01 | 7 | Complete |
| SEARCH-02 | 7 | Complete |
| SEARCH-03 | 7 | Complete |
| SEARCH-04 | 7 | Complete |
| SEARCH-05 | 7 | Complete |
| CONV-01 | 6 | Complete |
| CONV-02 | 6 | Complete |
| CONV-03 | 6 | Complete |
| CONV-04 | 6 | Complete |
| CONV-05 | 6 | Complete |
| TRANS-01 | 9 | Complete |
| TRANS-02 | 9 | Complete |
| TRANS-03 | 9 | Complete |
| TRANS-04 | 9 | Complete |
| TRANS-05 | 9 | Complete |
| TRANS-06 | 9 | Complete |
| MCP-01 | 10 | Pending |
| MCP-02 | 10 | Pending |
| MCP-03 | 10 | Pending |

**Coverage:**
- v1.1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 (100% coverage)

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 — traceability table filled, 100% coverage, phases 5-10*
