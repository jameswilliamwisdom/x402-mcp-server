---
phase: 03-brand-site-build
plan: "03"
subsystem: ui
tags: [astro, starlight, mdx, documentation, mcp]

requires:
  - phase: 03-01
    provides: Astro + Starlight scaffold with brand CSS and placeholder MDX stubs

provides:
  - Complete Getting Started guide (free mode + paid mode, all 4 MCP client configs)
  - Complete API Reference for all 6 MCP tools with parameter tables, pricing, and examples
  - Complete Wallet Setup guide (MetaMask → Base → USDC → private key export)
  - Placeholder PNG images for wallet setup steps

affects:
  - 03-04 (cross-cutting validation, npx -y check, pricing sync)
  - 04 (deployment — all doc pages must build clean)

tech-stack:
  added: []
  patterns:
    - "MDX JSX comments ({/* */}) required — HTML comments (<!-- -->) break MDX parser"
    - "Starlight Tabs with syncKey='mcp-client' keeps client selection in sync across multi-step guides"
    - "Placeholder images go in src/assets/ (Astro-optimized); must be valid PNGs (proper scanline filter bytes)"

key-files:
  created:
    - site/src/content/docs/getting-started.mdx
    - site/src/content/docs/api-reference.mdx
    - site/src/content/docs/wallet-setup.mdx
    - site/src/assets/wallet/placeholder-metamask-install.png
    - site/src/assets/wallet/placeholder-add-base.png
    - site/src/assets/wallet/placeholder-get-usdc.png
    - site/src/assets/wallet/placeholder-export-key.png
  modified: []

key-decisions:
  - "MDX comment syntax: use {/* */} not <!-- -->. Discovered during Task 2 build failure — HTML comments cause 'Unexpected character !' error in MDX parser."
  - "Placeholder PNGs must be valid with correct scanline filter bytes. Hand-crafted PNGs without proper IDAT structure cause 'invalid scanline filter' error in Astro's sharp optimizer."
  - "Wallet images placed in src/assets/ (not public/) to go through Astro's image optimization pipeline (converted to webp at build time)."

requirements-completed:
  - DOCS-01
  - DOCS-02
  - DOCS-03
  - DOCS-04

duration: 25min
completed: "2026-03-11"
---

# Phase 03 Plan 03: Documentation Pages Summary

**Three complete Starlight MDX docs pages: Getting Started (free+paid mode, 4 MCP clients), API Reference (all 6 tools), and Wallet Setup (MetaMask to private key export)**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-11T10:38:00Z
- **Completed:** 2026-03-11T10:44:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Getting Started guide: free mode path (screenshot of example.com) + paid mode path (BTC sentiment), with synced Tabs for all 4 MCP clients (Claude Desktop, Claude Code, Cursor, Windsurf), caution aside enforcing `npx -y`, and Common Issues section
- API Reference: single page covering all 6 tools with parameter tables, pricing, return descriptions, and conversational examples — matches prices in `src/index.ts` exactly
- Wallet Setup: step-by-step guide for crypto newcomers covering MetaMask install, Base network, USDC acquisition, and private key export; includes danger asides for key security
- All `npx` references use `-y` flag (grep-verified); cross-links between pages work correctly

## Task Commits

1. **Task 1: Getting Started guide** — `b0aa7a4` (docs)
2. **Task 2: API Reference** — `b593f9c` (docs)
3. **Task 3: Wallet Setup + placeholder images** — `b61af38` (docs)

## Files Created/Modified

- `site/src/content/docs/getting-started.mdx` — Free and paid mode quickstart with 4 MCP client configs, Common Issues, cross-links
- `site/src/content/docs/api-reference.mdx` — All 6 tools documented with parameter tables, pricing, examples, SYNC comment
- `site/src/content/docs/wallet-setup.mdx` — MetaMask → Base → USDC → private key guide with security asides
- `site/src/assets/wallet/placeholder-*.png` (4 files) — 800x400 valid gray placeholder PNGs for wallet steps

## Decisions Made

- **MDX JSX comments required:** HTML `<!-- -->` comments break MDX with "Unexpected character `!`" error. Used `{/* */}` JSX comment syntax for the SYNC note in api-reference.mdx. All future MDX comments must use JSX syntax.
- **Placeholder image format:** Images in `src/assets/` go through Astro's sharp optimizer. Hand-crafted PNGs must have valid scanline filter bytes in each row (filter type byte prepended to raw pixel data). Invalid PNGs fail with "invalid scanline filter" during Astro image optimization.
- **Placeholder images in src/assets/ (not public/):** Astro optimizes images in `src/assets/` to WebP at build time; `public/` images are served as-is. The MDX `![]()` syntax with `../../assets/` path uses Astro's image optimization — correct approach for real images. Placeholder images are small enough that optimization is trivial.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MDX HTML comment syntax broken**
- **Found during:** Task 2 (API Reference build)
- **Issue:** Plan specified adding a `<!-- SYNC: ... -->` comment in api-reference.mdx. MDX does not support HTML comment syntax — causes "Unexpected character `!`" parse error.
- **Fix:** Changed to JSX comment `{/* SYNC: ... */}` which is valid MDX syntax.
- **Files modified:** `site/src/content/docs/api-reference.mdx`
- **Verification:** Build passes after change
- **Committed in:** `b593f9c` (Task 2 commit)

**2. [Rule 1 - Bug] Invalid PNG scanline format rejected by sharp**
- **Found during:** Task 3 (Wallet Setup build)
- **Issue:** First attempt at placeholder PNGs used a simple hand-crafted structure missing proper per-row filter bytes. Astro's sharp image optimizer failed with "invalid scanline filter" error.
- **Fix:** Rewrote PNG generator to include filter type byte (0x00) prepended to each scanline row in the raw IDAT data. New PNGs pass sharp validation and are optimized to WebP at build time.
- **Files modified:** All 4 `site/src/assets/wallet/placeholder-*.png` files (regenerated)
- **Verification:** Build completes successfully, images optimized to WebP in dist/
- **Committed in:** `b61af38` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for build correctness. No scope changes.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plans 03-02 (landing page + pricing) and 03-03 (docs) are both complete, unblocking Plan 03-04
- Plan 03-04 is the cross-cutting validation pass: pricing sync check, npx -y grep, full build verification, visual spot-check
- All doc pages build clean and link correctly to each other

---
*Phase: 03-brand-site-build*
*Completed: 2026-03-11*
