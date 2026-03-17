# Roadmap: Bismuth (x402 API Network)

## Milestones

- **v1.0 npm Publish + Brand Site** — Phases 1-4 (shipped 2026-03-12)
- **v1.1 Universal Utility APIs** — Phases 5-10 (shipped 2026-03-15)
- **v2.0 Bismuth Launch** — Phases 11-16 (in progress)

## Phases

<details>
<summary>v1.0 npm Publish + Brand Site (Phases 1-4) — SHIPPED 2026-03-12</summary>

- [x] Phase 1: Package Hardening + Input Validation (2/2 plans) — 2026-03-09
- [x] Phase 2: npm Publish (1/1 plan) — 2026-03-10
- [x] Phase 3: Brand Site Build (4/4 plans) — 2026-03-11
- [x] Phase 4: Deployment (2/2 plans) — 2026-03-12

See [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

<details>
<summary>v1.1 Universal Utility APIs (Phases 5-10) — SHIPPED 2026-03-15</summary>

- [x] Phase 5: Web Scraping API (2/2 plans) — 2026-03-12
- [x] Phase 6: File Conversion API (2/2 plans) — 2026-03-13
- [x] Phase 7: Web Search API (2/2 plans) — 2026-03-14
- [x] Phase 8: Email Sending API (2/2 plans) — 2026-03-14
- [x] Phase 9: Audio Transcription API (2/2 plans) — 2026-03-15
- [x] Phase 10: MCP Server Update + npm Publish (2/2 plans) — 2026-03-15

See [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) for full details.

</details>

---

### v2.0 Bismuth Launch (In Progress)

**Milestone Goal:** Rebrand to Bismuth, go public on usebismuth.com with HTTPS, ship complete API reference docs, extend three backend APIs (email attachments/CC/BCC, DOCX-to-PDF, shallow site crawl), and publish x402-mcp-server@2.0.0.

- [x] **Phase 11: Rebrand + Domain + SSL** - Rename brand to Bismuth, register usebismuth.com, deploy site publicly with Cloudflare Tunnel HTTPS (2/2 plans created) (completed 2026-03-16)
- [x] **Phase 12: API Documentation** - Write 5 reference pages for all v1.1 APIs in Starlight with parameters, examples, and error codes (completed 2026-03-17)
- [x] **Phase 13: Email Attachments + CC/BCC** - Extend email API to accept CC, BCC, and base64 file attachments with size validation (completed 2026-03-17)
- [ ] **Phase 14: DOCX-to-PDF Conversion** - Add DOCX input type to conversion API via mammoth + WeasyPrint pipeline
- [ ] **Phase 15: Shallow Site Crawl** - New crawl endpoint on scraping API with BFS, 15-page sync cap, path filters, and per-URL SSRF validation
- [ ] **Phase 16: MCP Server Update + npm Publish** - Register x402_crawl_site, update email and convert Zod schemas, publish v2.0.0

## Phase Details

### Phase 11: Rebrand + Domain + SSL
**Goal**: Bismuth is publicly reachable at https://usebismuth.com with the new brand identity
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: BRAND-01, BRAND-02, BRAND-03, BRAND-04
**Success Criteria** (what must be TRUE):
  1. Visiting https://usebismuth.com loads the brand site over HTTPS with no browser security warnings
  2. All site content refers to "Bismuth" — no remaining "x402 API Network" copy
  3. Every page shows a "No API key — pay per call with USDC" message in a prominent position
  4. The site is reachable from the public internet, not just the local network
**Plans**: 11-01 (site rebrand — autonomous), 11-02 (domain + tunnel + deploy — requires human action)

### Phase 12: API Documentation
**Goal**: Every v1.1 API has a complete reference page with parameters, code examples, and free test endpoint link
**Depends on**: Phase 11 (domain must be live for docs links to resolve)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05
**Success Criteria** (what must be TRUE):
  1. Five reference pages exist in Starlight: Web Scraping, File Conversion, Web Search, Email Sending, Audio Transcription
  2. Each page contains a parameter table, curl example, MCP tool call example, and error code list
  3. The free test endpoint URL appears above the paid endpoint URL on each page
  4. All five pages appear correctly in the Starlight sidebar navigation
**Plans**: TBD

### Phase 13: Email Attachments + CC/BCC
**Goal**: Agents can send email with CC, BCC, and file attachments via the email API
**Depends on**: Phase 11 (for docs link correctness; backend can be developed in parallel)
**Requirements**: EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04
**Success Criteria** (what must be TRUE):
  1. A sent email arrives with CC recipients copied correctly
  2. A sent email arrives with BCC recipients blind-copied correctly
  3. A sent email arrives with a base64-encoded file attachment preserved
  4. Submitting an attachment over 25MB pre-encoding returns a clear validation error before any network call
**Plans**: TBD

### Phase 14: DOCX-to-PDF Conversion
**Goal**: Agents can convert DOCX files to PDF via the conversion API using the mammoth + WeasyPrint pipeline
**Depends on**: Phase 11 (for docs link correctness; backend can be developed in parallel)
**Requirements**: CONV-01, CONV-02, CONV-03
**Success Criteria** (what must be TRUE):
  1. Submitting a DOCX file with type "docx" to x402_convert_file returns a base64-encoded PDF
  2. The returned PDF preserves the document's text content, headings, tables, and embedded images
  3. The API docs page for File Conversion explicitly notes the conversion is content-document fidelity, not layout-preserving
**Plans**: 2 plans (Wave 1 parallel)
- [ ] 14-01-PLAN.md — Backend: mammoth dependency, sync_docx_to_pdf function, Pydantic model + dispatch (autonomous)
- [ ] 14-02-PLAN.md — MCP tool Zod schema extension + docs update with CONV-03 fidelity note (autonomous)

### Phase 15: Shallow Site Crawl
**Goal**: Agents can crawl a site's pages and receive structured per-page extraction results via a single tool call
**Depends on**: Phase 11 (for docs link correctness; backend can be developed in parallel)
**Requirements**: CRAWL-01, CRAWL-02, CRAWL-03, CRAWL-04, CRAWL-05, CRAWL-06, CRAWL-07, CRAWL-08
**Success Criteria** (what must be TRUE):
  1. Calling x402_crawl_site with a seed URL returns per-page extraction results in the same schema as x402_scrape_url
  2. The crawl stops at the max_pages limit (default 10, hard cap 15) and respects max_depth
  3. Include and exclude path filters correctly limit which URLs are crawled
  4. Every discovered URL — not just the seed URL — passes SSRF validation before being fetched
  5. The response includes metadata (pages_requested, pages_crawled, pages_skipped, reasons_skipped) and partial results are returned if some pages fail
**Plans**: TBD

### Phase 16: MCP Server Update + npm Publish
**Goal**: x402-mcp-server@2.0.0 is published to npm with all 12 tools and Bismuth branding
**Depends on**: Phases 13, 14, 15 (all backend endpoints must be deployed and verified before publish)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05
**Success Criteria** (what must be TRUE):
  1. npm install x402-mcp-server installs version 2.0.0
  2. The x402_crawl_site tool is available and calls the deployed /crawl endpoint
  3. x402_send_email accepts cc, bcc, and attachments parameters without error
  4. x402_convert_file accepts type "docx" and returns a PDF
  5. The README lists all 12 tools with Bismuth branding and correct endpoint URLs
**Plans**: TBD

## Progress

**Execution Order:** 11 → 12 → 13 → 14 → 15 → 16
(Phases 13, 14, 15 are backend-independent and can be developed in parallel; Phase 16 requires all three to be deployed)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Package Hardening + Input Validation | v1.0 | 2/2 | Complete | 2026-03-09 |
| 2. npm Publish | v1.0 | 1/1 | Complete | 2026-03-10 |
| 3. Brand Site Build | v1.0 | 4/4 | Complete | 2026-03-11 |
| 4. Deployment | v1.0 | 2/2 | Complete | 2026-03-12 |
| 5. Web Scraping API | v1.1 | 2/2 | Complete | 2026-03-12 |
| 6. File Conversion API | v1.1 | 2/2 | Complete | 2026-03-13 |
| 7. Web Search API | v1.1 | 2/2 | Complete | 2026-03-14 |
| 8. Email Sending API | v1.1 | 2/2 | Complete | 2026-03-14 |
| 9. Audio Transcription API | v1.1 | 2/2 | Complete | 2026-03-15 |
| 10. MCP Server Update + npm Publish | v1.1 | 2/2 | Complete | 2026-03-15 |
| 11. Rebrand + Domain + SSL | 2/2 | Complete    | 2026-03-16 | - |
| 12. API Documentation | 2/2 | Complete    | 2026-03-17 | - |
| 13. Email Attachments + CC/BCC | 2/2 | Complete    | 2026-03-17 | - |
| 14. DOCX-to-PDF Conversion | v2.0 | 0/2 | Planned | - |
| 15. Shallow Site Crawl | v2.0 | 0/TBD | Not started | - |
| 16. MCP Server Update + npm Publish | v2.0 | 0/TBD | Not started | - |

---

*Roadmap created: 2026-03-09*
*Last updated: 2026-03-16 — v2.0 Bismuth Launch phases 11-16 added*
