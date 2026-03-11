# Phase 3: Brand Site Build - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Scaffold and populate the Astro + Starlight brand site in `site/` with all marketing and documentation content. Fully custom landing page + Starlight docs. The site lives in the same repo but has its own `package.json` so Astro never enters the npm bundle.

</domain>

<decisions>
## Implementation Decisions

### Visual Identity
- Dark mode only — no light mode toggle
- Color palette: Protocol Green (#4ADE80) accent on black (#000000) backgrounds
- Full brand guidelines at `assets/brand-guidelines.md` — colors, typography, logo usage, voice & tone
- Typography: Space Grotesk for headlines/marketing, JetBrains Mono for code/pricing/endpoints
- CSS tokens defined in brand guidelines (--x402-green, --x402-bg, --x402-surface, etc.)

### Logo
- User-provided logo: `~/Desktop/NanoBananaImages/nano-banana-2026-03-11T02-46-12-720Z-s2tslw.png` (mark only)
- Full lockup also available: `nano-banana-2026-03-11T03-25-22-999Z-ucijia.png`
- Copy both to `site/public/` during scaffold
- Green X arrows on black — represents bilateral value flow between agents and APIs

### OG Image
- Dark card with title + tagline — match the dark + neon green identity
- 1200x630, full lockup on black per brand guidelines

### Homepage
- Fully custom Astro page (NOT Starlight template) — Starlight handles docs pages only
- Primary CTA: "Get Started" linking to free mode Getting Started guide
- Pricing: brief summary on homepage + separate detailed pricing page
- How it works: one-liner only — "HTTP 402 → USDC payment → API response. That's the whole protocol."
- Hero section with one-liner pitch, value prop bullets, CTA button

### Content Tone & Audience
- Audience: both AI/MCP developers AND crypto-native builders — explain both MCP and crypto concepts
- Voice follows brand guidelines: technical, confident, concise
- Getting Started guide includes all 4 MCP client configs (Claude Desktop, Claude Code, Cursor, Windsurf)

### Wallet Setup Guide
- Step-by-step with annotated placeholder images (not real MetaMask screenshots — won't break on UI updates)
- Full walkthrough: MetaMask install, add Base network, get USDC, export private key
- Covers complete crypto-newcomer path

### API Reference
- Moderate depth: parameter table + one example per tool
- Code examples: conversational style ("Ask your AI agent: 'Take a screenshot of example.com'")
- API page layout: Claude's discretion (single page vs per-tool)

### Getting Started Flow
- Example progression: free mode (screenshot of example.com) → paid mode (crypto sentiment for BTC)
- Troubleshooting: inline "Common Issues" section at bottom of Getting Started (not separate page)
- Common issues to cover: npx without -y, @x402/fetch vs x402-fetch, insufficient USDC, Node version

### Claude's Discretion
- Docs tone calibration (sharp for reference, approachable for tutorials)
- API reference layout (single page vs per-tool pages)
- Homepage hero layout and spacing
- Starlight sidebar navigation structure
- Exact Starlight configuration and theme customization approach

</decisions>

<specifics>
## Specific Ideas

- Brand guidelines already define the full visual system — `assets/brand-guidelines.md` is the source of truth
- Logo semantics: "two interlocking arrows forming an X — representing the bilateral flow of value between AI agents and API services"
- Voice examples from brand guidelines: "Pay $0.01 in USDC on Base. Get a screenshot. One HTTP request."
- Pairing rule: "Space Grotesk speaks to humans. JetBrains Mono speaks to machines."
- Homepage how-it-works as one-liner keeps the page tight — detailed flow lives in docs if needed

</specifics>

<deferred>
## Deferred Ideas

- Changelog / "What's New" page — skip for v1, add when there's version history to track
- Interactive API playground — v2 requirement (DEV-01)
- Real MetaMask screenshots — using placeholder images for now, consider updating post-launch

</deferred>

---

*Phase: 03-brand-site-build*
*Context gathered: 2026-03-11*
