# Requirements: x402 API Network

**Defined:** 2026-03-12
**Core Value:** AI agents can discover and pay for useful APIs with zero integration friction

## v1.1 Requirements

Requirements for milestone v1.1 — Universal Utility APIs. Each maps to roadmap phases.

### Web Scraping

- [ ] **SCRAPE-01**: Given a URL, return structured JSON with markdown text, extracted links, and page metadata
- [ ] **SCRAPE-02**: JS-rendered pages supported via Playwright (not just static HTML)
- [ ] **SCRAPE-03**: `wait_for` CSS selector parameter for async SPA content
- [ ] **SCRAPE-04**: SSRF protection — server-side IP validation rejects private/loopback ranges
- [ ] **SCRAPE-05**: Free test endpoint with fixture data (no live scraping)

### Email Sending

- [ ] **EMAIL-01**: Send email with to, subject, plain text body via Resend
- [ ] **EMAIL-02**: HTML body support with auto plain-text fallback
- [ ] **EMAIL-03**: Verified sender domain with SPF/DKIM/DMARC configured
- [ ] **EMAIL-04**: Abuse limits — rate limit per wallet (10 sends/day)
- [ ] **EMAIL-05**: Free test endpoint (sandbox mode, no real delivery)

### Web Search

- [ ] **SEARCH-01**: Given a query, return top N results (title, URL, snippet) as JSON via Tavily
- [ ] **SEARCH-02**: `include_answer` param — synthesized answer with sources
- [ ] **SEARCH-03**: `include_domains`/`exclude_domains` for focused research
- [ ] **SEARCH-04**: Per-wallet daily query limit to prevent cost spikes
- [ ] **SEARCH-05**: Free test endpoint with fixture data

### File Conversion

- [ ] **CONV-01**: Image resize/reformat (Pillow) — input URL + target dimensions/format
- [ ] **CONV-02**: CSV→JSON conversion (Python stdlib)
- [ ] **CONV-03**: HTML→PDF conversion (WeasyPrint)
- [ ] **CONV-04**: SSRF protection on file fetch URLs
- [ ] **CONV-05**: Free test endpoint with fixture data

### Audio Transcription

- [ ] **TRANS-01**: Given an audio URL, return text transcript via faster-whisper on home server
- [ ] **TRANS-02**: Auto language detection with detected language in response
- [ ] **TRANS-03**: Optional word-level timestamps
- [ ] **TRANS-04**: Language hint parameter for known languages
- [ ] **TRANS-05**: Size/duration limits (25MB / 60 min) with clear error messages
- [ ] **TRANS-06**: Free test endpoint with fixture data

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
| SCRAPE-01 | — | Pending |
| SCRAPE-02 | — | Pending |
| SCRAPE-03 | — | Pending |
| SCRAPE-04 | — | Pending |
| SCRAPE-05 | — | Pending |
| EMAIL-01 | — | Pending |
| EMAIL-02 | — | Pending |
| EMAIL-03 | — | Pending |
| EMAIL-04 | — | Pending |
| EMAIL-05 | — | Pending |
| SEARCH-01 | — | Pending |
| SEARCH-02 | — | Pending |
| SEARCH-03 | — | Pending |
| SEARCH-04 | — | Pending |
| SEARCH-05 | — | Pending |
| CONV-01 | — | Pending |
| CONV-02 | — | Pending |
| CONV-03 | — | Pending |
| CONV-04 | — | Pending |
| CONV-05 | — | Pending |
| TRANS-01 | — | Pending |
| TRANS-02 | — | Pending |
| TRANS-03 | — | Pending |
| TRANS-04 | — | Pending |
| TRANS-05 | — | Pending |
| TRANS-06 | — | Pending |
| MCP-01 | — | Pending |
| MCP-02 | — | Pending |
| MCP-03 | — | Pending |

**Coverage:**
- v1.1 requirements: 29 total
- Mapped to phases: 0
- Unmapped: 29 ⚠️ (pending roadmap creation)

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 — initial definition*
