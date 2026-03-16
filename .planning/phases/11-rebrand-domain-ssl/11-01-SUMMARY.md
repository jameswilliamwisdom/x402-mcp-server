---
phase: 11-rebrand-domain-ssl
plan: "01"
subsystem: site-content
tags: [rebrand, bismuth, copy, docs, brand-audit]
dependency_graph:
  requires: []
  provides: [BRAND-01, BRAND-03, BRAND-04]
  affects: [site/astro.config.mjs, site/src/pages/index.astro, site/src/pages/pricing.astro, site/src/components/landing/Hero.astro, site/src/components/landing/Footer.astro, site/src/content/docs/getting-started.mdx, site/src/content/docs/api-reference.mdx, site/src/content/docs/wallet-setup.mdx]
tech_stack:
  added: []
  patterns: [brand-copy-pass, no-api-key-messaging, free-before-paid-endpoint]
key_files:
  created: []
  modified:
    - site/astro.config.mjs
    - site/src/pages/index.astro
    - site/src/pages/pricing.astro
    - site/src/components/landing/Hero.astro
    - site/src/components/landing/Footer.astro
    - site/src/content/docs/getting-started.mdx
    - site/src/content/docs/api-reference.mdx
    - site/src/content/docs/wallet-setup.mdx
decisions:
  - "MCP tool names (x402_*), package name (x402-mcp-server), and env var (X402_PRIVATE_KEY) intentionally kept as-is — only brand copy changes"
  - "pricing.astro fixed as Rule 2 auto-fix — was not in plan file list but had stray x402 Network and x402.todo references"
metrics:
  duration: "245 seconds"
  completed_date: "2026-03-16"
  tasks_completed: 5
  files_modified: 8
---

# Phase 11 Plan 01: Site Content Rebrand to Bismuth Summary

Pure content/copy rebrand pass replacing all "x402 API Network" and "x402 Network" brand references with "Bismuth" across all site source files. Added "No API key — pay per call with USDC" messaging to landing page Hero and every paid tool section in the API reference. Added free test endpoint URLs prominently above paid endpoint URLs on each tool section.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update astro.config.mjs — Bismuth title + usebismuth.com SITE_URL | 8655b8f | site/astro.config.mjs |
| 2 | Update landing page — index.astro, Hero.astro, Footer.astro | 59aa70e | site/src/pages/index.astro, Hero.astro, Footer.astro |
| 3 | Update docs — getting-started.mdx and wallet-setup.mdx | 89ee61c | site/src/content/docs/getting-started.mdx, wallet-setup.mdx |
| 4 | Update api-reference.mdx — Bismuth branding + no-API-key Asides + free test endpoint URLs | e3ea1bc | site/src/content/docs/api-reference.mdx |
| 5 | Verify no stray brand references remain (+ fix pricing.astro) | 625dbe2 | site/src/pages/pricing.astro |

## Files Modified and What Changed

**site/astro.config.mjs**
- `title` changed from `'x402'` to `'Bismuth'`
- `description` updated to reference Bismuth and USDC
- `SITE_URL` fallback changed from `https://x402.todo` to `https://usebismuth.com`
- OG image URL fallback changed from `https://x402.todo` to `https://usebismuth.com`

**site/src/pages/index.astro**
- `<title>` changed to `Bismuth — Pay-per-use APIs for AI Agents`
- `og:title` and `twitter:title` updated to Bismuth
- `og:description`, `twitter:description`, and meta description updated with no-API-key messaging
- `SITE_URL` fallback changed to `https://usebismuth.com`

**site/src/components/landing/Hero.astro**
- Logo `alt` attribute changed from `x402 Network` to `Bismuth`
- Added first value-prop bullet: "No API key — pay per call with USDC, no subscription required"

**site/src/components/landing/Footer.astro**
- Link text changed from `x402 Network` to `Bismuth`

**site/src/content/docs/getting-started.mdx**
- Frontmatter `description` updated to reference "Bismuth MCP server"
- Intro paragraph changed from "x402 gives" to "Bismuth gives"; appended "No API key required — every call is a micropayment."

**site/src/content/docs/wallet-setup.mdx**
- Frontmatter `description` updated: "paid x402 APIs" → "paid Bismuth APIs"
- Intro paragraph updated: "paid x402 APIs" → "paid Bismuth APIs"

**site/src/content/docs/api-reference.mdx**
- Description updated to "11 Bismuth MCP tools"
- Intro paragraph updated to "Bismuth exposes 11 MCP tools" with no-API-key messaging
- Added top-of-page `<Aside type="tip" title="No API key required">` with x402 micropayment protocol explanation
- Added free test endpoint URL above paid endpoint URL for every paid tool section (5 tools)
- Added per-tool `<Aside type="tip">No API key required. Add X402_PRIVATE_KEY...</Aside>` to each paid tool section
- Pricing summary table expanded from 6 to 11 tools (added v1.1 tools with prices)
- Closing paragraph updated to direct to free test first, then wallet for paid

**site/src/pages/pricing.astro** (auto-fix, not in original plan file list)
- Title, og:title, twitter:title updated from "Pricing — x402 Network" to "Pricing — Bismuth"
- SITE_URL fallback changed from `x402.todo` to `usebismuth.com`
- Nav logo alt and nav brand text updated from `x402` to `Bismuth`

## Brand Reference Audit Results

```
grep -rn "x402 API Network" site/src/  → 0 matches (PASS)
grep -rn "x402 Network" site/src/      → 0 matches (PASS)
grep -rn "x402.todo" site/src/ site/astro.config.mjs → 0 matches (PASS)
grep -rn "Bismuth" site/src/           → 19 matches (>= 10 required, PASS)
```

## Requirements Satisfied

- **BRAND-01:** Zero occurrences of "x402 API Network", "x402 Network", or "x402.todo" in site/src/ and site/astro.config.mjs. Confirmed by grep.
- **BRAND-03:** "No API key — pay per call with USDC" messaging present in Hero.astro (landing page), top-of-page Aside in api-reference.mdx, and individual Aside on every paid tool section in api-reference.mdx. 8 occurrences of "No API key" across api-reference.mdx and Hero.astro.
- **BRAND-04:** Free test endpoint URL appears before paid endpoint URL on every tool section in api-reference.mdx. Verified with line number output showing consecutive Free/Paid pairs (lines 44/45, 86/87, 118/119, 150/151, 177/178).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Fixed stray brand references in pricing.astro**
- **Found during:** Task 5 (brand audit)
- **Issue:** pricing.astro contained "x402 Network" in title/og/twitter title tags and "x402.todo" in SITE_URL fallback. The file was not listed in the plan's `files_modified` frontmatter but was caught by the Task 5 brand audit grep.
- **Fix:** Updated title, og:title, twitter:title to use "Bismuth"; updated SITE_URL fallback to usebismuth.com; updated nav logo alt and nav brand text from "x402" to "Bismuth"
- **Files modified:** site/src/pages/pricing.astro
- **Commit:** 625dbe2

## Self-Check: PASSED

All 8 modified files confirmed to exist on disk. All 5 task commits (8655b8f, 59aa70e, 89ee61c, e3ea1bc, 625dbe2) confirmed in git log.
