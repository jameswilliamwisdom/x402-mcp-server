---
plan: 03-02
phase: 03-brand-site-build
status: complete
completed: "2026-03-11"
tasks_total: 2
tasks_completed: 2
commits:
  - "feat(site): build custom landing page with Hero, HowItWorks, PricingSummary, Footer (03-02 Task 1)"
  - "feat(site): build pricing page with full tool table and USDC payment info (03-02 Task 2)"
---

# Plan 03-02 Summary: Landing Page + Pricing Page

## What Was Built

Two custom marketing pages outside the Starlight docs shell — the primary entry points for developers discovering x402.

### Task 1: Landing Page

**Files created/modified:**
- `site/src/pages/index.astro` — Full custom landing page (replaced 03-01 placeholder)
- `site/src/components/landing/Hero.astro` — Hero section
- `site/src/components/landing/HowItWorks.astro` — Protocol one-liner
- `site/src/components/landing/PricingSummary.astro` — Pricing overview table
- `site/src/components/landing/Footer.astro` — Minimal footer

**Hero:** Logo lockup with green radial glow, one-liner pitch ("Pay-per-use APIs for AI agents. One npm install, automatic USDC micropayments on Base."), 3 value prop bullets, Protocol Green "Get Started" CTA → `/getting-started/`, secondary "View Pricing" → `/pricing/`.

**HowItWorks:** Single-line protocol explanation in JetBrains Mono per brand pairing rule — speaks to machines. Bordered strip visually separating hero from pricing.

**PricingSummary:** Striped table of all 6 tools with individual prices in JetBrains Mono. "See full pricing →" link to `/pricing/`. Prices match `src/index.ts` exactly.

**index.astro:** Full custom page — not Starlight. `data-theme="dark"` on `<html>`. Complete `<head>` with OG tags (absolute URLs using `import.meta.env.SITE`), Twitter Card, Google Fonts, favicon.

### Task 2: Pricing Page

**Files created:**
- `site/src/pages/pricing.astro` — Full custom pricing page at `/pricing/`
- `site/src/components/pricing/PricingTable.astro` — Data-driven tool table

**PricingTable:** Typed `Tool[]` array with all 6 MCP tools. SYNC comment points to `src/index.ts`. Columns: Tool (name + description), Tool ID (JetBrains Mono), Price/call (Protocol Green JetBrains Mono), Free Mode badge. Responsive — collapses to stacked layout at ≤640px.

**pricing.astro:** Full custom page with top nav (logo + links), page header, USDC payment info bar (JetBrains Mono), PricingTable, CTA button → `/getting-started/`. Same dark mode setup as index.astro.

## Verification Results

All 8 plan verification checks pass:
1. `npm run build` exits 0 (6 pages built)
2. `dist/index.html` contains "Get Started" CTA
3. `dist/index.html` links to `/getting-started/`
4. `og:image` in `dist/index.html` uses absolute HTTPS URL
5. `dist/pricing/index.html` exists
6. All 6 tool IDs present (`x402_network_info` through `x402_intelligence`)
7. Pricing values $0.01, $0.05, $0.10 present
8. Both pages have `data-theme="dark"` on `<html>`

## Decisions Made

- **PricingSummary uses a striped table** (not a card grid) for compact display of 6 tools — card grid would be too tall for a homepage section.
- **pricing.astro includes top nav** — standalone page needs navigation context since it's outside Starlight's chrome.
- **SYNC comment strategy**: inline `// SYNC: prices must match src/index.ts` comments on both PricingSummary.astro and PricingTable.astro. A shared `pricing.ts` constant is deferred until a third API is added or pricing changes (per STATE.md note).
- **Free mode badge on all tools**: all tools support free test mode. Badge is consistent across the table.

## Requirements Satisfied

- SITE-01: Developer lands on homepage, reads one-liner pitch within 2 seconds, reaches Getting Started in one click
- SITE-02: Pricing table at `/pricing/` shows all 6 tools with exact per-call costs matching `src/index.ts`
- SITE-03: Homepage shows "HTTP 402 → USDC payment → API response" protocol explanation
- SITE-04: Both pages have complete OG meta tags with absolute URLs
