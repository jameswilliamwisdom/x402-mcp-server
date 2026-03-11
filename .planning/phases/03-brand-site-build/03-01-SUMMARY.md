---
plan: 03-01
phase: 03-brand-site-build
completed: "2026-03-11"
status: complete
commits:
  - d546b17: "feat(site): scaffold Astro 5 + Starlight 0.37.7 with static output and brand theming"
  - aa693e1: "feat(site): add brand logo assets and OG image to site/public"
---

# Summary: 03-01 — Astro + Starlight Scaffold, Brand Theming, Logo Assets

## What Was Done

Scaffolded the Astro + Starlight site in `site/` with full brand theming, dark mode enforcement, and all logo/OG assets. This is the foundation for Plans 03-02 and 03-03.

## Tasks Completed

### Task 1: Scaffold Astro + Starlight and configure project
- Created `site/package.json` with `astro ^5.18.0` and `@astrojs/starlight ^0.37.7`
- Created `site/astro.config.mjs` with full config: `output: 'static'`, Starlight integration, dark mode component overrides, dual `customCss`, Google Fonts `<link>` in `head:`, OG/twitter meta tags, manual sidebar, `favicon: '/logo-mark.png'`
- Created `site/tsconfig.json` extending `astro/tsconfigs/strict`
- Created `site/src/content.config.ts` with `docsLoader()` + `docsSchema()` (root-level, not deprecated `src/content/config.ts`)
- Created placeholder docs: `getting-started.mdx`, `wallet-setup.mdx`, `api-reference.mdx`
- Created minimal `site/src/pages/index.astro` (replaced by Plan 03-02)
- Build verified: `site/dist/index.html` exists, no `_server/` directory

### Task 2: Apply brand CSS tokens, Starlight overrides, and dark mode enforcement
- Created `site/src/styles/global.css` — all 11 `--x402-*` brand tokens exactly matching `assets/brand-guidelines.md`
- Created `site/src/styles/starlight.css` — maps `--x402-*` onto `--sl-color-*` and `--sl-font-*` variables
- Created `site/src/components/ForceDarkTheme.astro` — `is:inline` script sets `data-theme="dark"` synchronously (FOLIOM prevention)
- Created `site/src/components/EmptyComponent.astro` — removes theme toggle
- Both referenced in `astro.config.mjs` `components` overrides

### Task 3: Copy logo assets and generate OG image
- Copied `logo-mark.png` from `~/Desktop/NanoBananaImages/nano-banana-2026-03-11T02-46-12-720Z-s2tslw.png`
- Copied `logo-lockup.png` from `~/Desktop/NanoBananaImages/nano-banana-2026-03-11T03-25-31-811Z-hg4o5e.png` (closest available match to expected filename)
- Generated `og-image.png` at 1200x630 using Nano Banana MCP + `sips` canvas resize: dark card, Protocol Green X arrows, X402 NETWORK wordmark, tagline

## Decisions Made

### Zod Version Override Required
- **Problem:** `@astrojs/sitemap@3.7.1` (a Starlight dependency) requires `zod@^4.3.6`, while Astro 5 uses `zod@3.x`. npm resolved the root `zod` to 4.x, which broke Starlight's schema (`_zod` property not found on Zod 3 objects).
- **Fix:** Added `overrides` in `site/package.json` to pin `zod` to `3.25.76` and `@astrojs/sitemap` to `3.6.1` (last version using Zod 3). Build succeeds with all Zod at 3.x.
- **Note for future:** When upgrading Starlight, check if `@astrojs/sitemap` has been updated to support Zod 4 natively — if so, remove the overrides.

### Logo Lockup File Selection
- The expected filename `nano-banana-2026-03-11T03-25-22-999Z-ucijia.png` was not present in `~/Desktop/NanoBananaImages/`. Used `nano-banana-2026-03-11T03-25-31-811Z-hg4o5e.png` (same session, seconds later) — the cleaner X-arrows-with-bracket design.

### OG Image Dimensions
- Nano Banana generates 1024x1024. Used `sips -z 630 630` to scale to square then `sips -c 630 1200` to canvas-extend to 1200x630 with black padding. Result is correct 1200x630 landscape OG format.

### Tasks 1 and 2 in Single Commit
- Tasks 1 and 2 are interdependent: `astro.config.mjs` references the CSS and component files, so all had to exist for the build to pass. Both tasks committed together in `d546b17` as a clean atomic unit.

## Verification Results

All 7 plan verification checks passed:
1. `npm run build` exits 0 inside `site/`
2. `site/dist/index.html` exists
3. No `site/dist/_server/` or `site/dist/_functions/` directory
4. `data-theme="dark"` present in `dist/getting-started/index.html` `<html>` element
5. All three assets present: `logo-mark.png`, `logo-lockup.png`, `og-image.png`
6. `--x402-green` defined in `src/styles/global.css`
7. `--sl-color-accent` defined in `src/styles/starlight.css`

## Files Created

| File | Purpose |
|------|---------|
| `site/package.json` | Isolated Astro + Starlight deps; Zod overrides |
| `site/package-lock.json` | Lockfile for reproducible installs |
| `site/astro.config.mjs` | Full Astro + Starlight config |
| `site/tsconfig.json` | TypeScript strict config |
| `site/src/content.config.ts` | Content collection: docsLoader + docsSchema |
| `site/src/pages/index.astro` | Placeholder homepage (replaced by 03-02) |
| `site/src/content/docs/getting-started.mdx` | Stub doc (replaced by 03-03) |
| `site/src/content/docs/wallet-setup.mdx` | Stub doc (replaced by 03-03) |
| `site/src/content/docs/api-reference.mdx` | Stub doc (replaced by 03-03) |
| `site/src/styles/global.css` | Brand CSS tokens (--x402-*) |
| `site/src/styles/starlight.css` | Starlight variable overrides (--sl-*) |
| `site/src/components/ForceDarkTheme.astro` | FOLIOM-free dark mode enforcement |
| `site/src/components/EmptyComponent.astro` | Theme toggle removal |
| `site/public/logo-mark.png` | Brand mark only |
| `site/public/logo-lockup.png` | Full mark + wordmark lockup |
| `site/public/og-image.png` | 1200x630 OG card |
