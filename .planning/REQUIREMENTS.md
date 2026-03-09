# Requirements: x402 API Network

**Defined:** 2026-03-09
**Core Value:** AI agents can discover and pay for useful APIs with zero integration friction

## v1 Requirements

Requirements for milestone v1.0 — Publish + Brand. Each maps to roadmap phases.

### Package Hardening

- [ ] **PKG-01**: `files` whitelist in package.json limits published content to `dist/`, `README.md`, `LICENSE`
- [ ] **PKG-02**: `prepublishOnly` script runs `tsc` build before every publish
- [ ] **PKG-03**: `engines` field declares Node 18+ requirement
- [ ] **PKG-04**: LICENSE file exists on disk (MIT)
- [ ] **PKG-05**: Shebang (`#!/usr/bin/env node`) preserved in `dist/index.js` after compilation
- [ ] **PKG-06**: `publint` validates package exports before publish

### Input Validation

- [ ] **VAL-01**: `coin` parameter validated with `/^[A-Z0-9]{1,10}$/i` regex
- [ ] **VAL-02**: `url` and `pdf_url` parameters validated with `z.string().url()`

### npm Publish

- [ ] **NPM-01**: README updated with npm install instructions and Claude config example (using `npx -y`)
- [ ] **NPM-02**: Package published to npm registry as `x402-mcp-server`

### Brand Site — Marketing

- [ ] **SITE-01**: Hero section with one-liner pitch and value proposition
- [ ] **SITE-02**: Pricing table showing all tools with per-call costs
- [ ] **SITE-03**: "How it works" section explaining x402 payment flow
- [ ] **SITE-04**: OG meta tags for link sharing

### Brand Site — Documentation

- [ ] **DOCS-01**: Getting started guide with free mode and paid mode paths
- [ ] **DOCS-02**: API reference for all 6 MCP tools (params, returns, examples)
- [ ] **DOCS-03**: Claude/MCP config example (copy-pasteable JSON)
- [ ] **DOCS-04**: Wallet setup guide (Base network, USDC funding)

### Deployment

- [ ] **DEPLOY-01**: Astro site builds to static output
- [ ] **DEPLOY-02**: Site deployed to home server (no domain, IP/subdomain for now)

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Developer Platform

- **DEV-01**: Interactive API playground on brand site
- **DEV-02**: SDK / client library for programmatic access
- **DEV-03**: Usage dashboard / analytics

### Infrastructure

- **INFRA-01**: Custom domain with SSL for brand site
- **INFRA-02**: CI/CD pipeline for automated npm publish
- **INFRA-03**: Uptime monitoring page

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / API keys | Private key IS the account — Phase 3 |
| Third-party API hosting | Phase 3 — developer platform |
| Own L2 chain | Phase 4 — far future |
| Mobile app | Not planned |
| Interactive API playground | Requires backend proxy — v2 |
| Automated CI/CD publish | Manual publish for v1.0 — adds secrets complexity |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | — | Pending |
| PKG-02 | — | Pending |
| PKG-03 | — | Pending |
| PKG-04 | — | Pending |
| PKG-05 | — | Pending |
| PKG-06 | — | Pending |
| VAL-01 | — | Pending |
| VAL-02 | — | Pending |
| NPM-01 | — | Pending |
| NPM-02 | — | Pending |
| SITE-01 | — | Pending |
| SITE-02 | — | Pending |
| SITE-03 | — | Pending |
| SITE-04 | — | Pending |
| DOCS-01 | — | Pending |
| DOCS-02 | — | Pending |
| DOCS-03 | — | Pending |
| DOCS-04 | — | Pending |
| DEPLOY-01 | — | Pending |
| DEPLOY-02 | — | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 0
- Unmapped: 20 ⚠️

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after initial definition*
