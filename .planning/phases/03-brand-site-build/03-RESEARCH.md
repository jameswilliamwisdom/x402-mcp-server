# Phase 3: Brand Site Build - Research

**Researched:** 2026-03-10
**Domain:** Astro + Starlight static site — marketing and documentation
**Confidence:** HIGH (all three dimensions at HIGH; one MEDIUM-confidence pitfall on route collision behavior)
**Method:** MECE decomposition (3 dimensions: STACK, UX, PITFALLS)

---

## Summary

Phase 3 builds the x402 brand site in `site/` — an isolated Astro + Starlight project with its own `package.json` that never enters the root npm bundle. The site has two distinct routing systems: a fully custom Astro landing page (and pricing page) at `src/pages/`, and Starlight-managed documentation pages at `src/content/docs/`. These coexist without conflict as long as no `src/content/docs/index.md` is created (which would collide with `src/pages/index.astro`).

The stack is locked: Astro 5.18.x (NOT 6.x — Starlight 0.37.7 requires `astro ^5.5.0`; Astro 6.0.0 shipped today and Starlight has not yet released explicit support). Starlight 0.37.7 handles all documentation plumbing — sidebar, Pagefind search, Expressive Code syntax highlighting, and i18n — with zero extra configuration. Brand theming runs through two CSS layers: `--x402-*` tokens in `global.css` for brand values, mapped onto `--sl-color-*` variables in `starlight.css` via `customCss`. Dark mode is enforced by overriding Starlight's `ThemeProvider` with an inline-script component that sets `data-theme="dark"` synchronously before first paint, eliminating any flash of light mode.

OG image generation uses a static `og.png` placed in `site/public/` — for a single static card, a pre-generated image is simpler and more reliable than a dynamic satori/sharp endpoint. If build-time dynamic generation is needed (per-page OG images), the satori + sharp pattern is documented with its critical constraint: satori requires local `.ttf` font files; Google Fonts CDN URLs are not usable at build time. The `site:` field in `astro.config.mjs` must be set to an absolute URL before production build; use `process.env.SITE_URL` so a placeholder during Phase 3 can be swapped at Phase 4 deploy time without a code change.

**Primary recommendation:** Scaffold `site/` with Astro 5.18.x + Starlight 0.37.7, apply the dual-CSS-layer theming approach, enforce dark mode via component override, and use a pre-generated static `og.png` unless per-page OG images become a requirement.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Visual Identity
- Dark mode only — no light mode toggle
- Color palette: Protocol Green (#4ADE80) accent on black (#000000) backgrounds
- Full brand guidelines at `assets/brand-guidelines.md` — colors, typography, logo usage, voice & tone
- Typography: Space Grotesk for headlines/marketing, JetBrains Mono for code/pricing/endpoints
- CSS tokens defined in brand guidelines (--x402-green, --x402-bg, --x402-surface, etc.)

#### Logo
- User-provided logo: `~/Desktop/NanoBananaImages/nano-banana-2026-03-11T02-46-12-720Z-s2tslw.png` (mark only)
- Full lockup also available: `nano-banana-2026-03-11T03-25-22-999Z-ucijia.png`
- Copy both to `site/public/` during scaffold
- Green X arrows on black — represents bilateral value flow between agents and APIs

#### OG Image
- Dark card with title + tagline — match the dark + neon green identity
- 1200x630, full lockup on black per brand guidelines

#### Homepage
- Fully custom Astro page (NOT Starlight template) — Starlight handles docs pages only
- Primary CTA: "Get Started" linking to free mode Getting Started guide
- Pricing: brief summary on homepage + separate detailed pricing page
- How it works: one-liner only — "HTTP 402 → USDC payment → API response. That's the whole protocol."
- Hero section with one-liner pitch, value prop bullets, CTA button

#### Content Tone & Audience
- Audience: both AI/MCP developers AND crypto-native builders — explain both MCP and crypto concepts
- Voice follows brand guidelines: technical, confident, concise
- Getting Started guide includes all 4 MCP client configs (Claude Desktop, Claude Code, Cursor, Windsurf)

#### Wallet Setup Guide
- Step-by-step with annotated placeholder images (not real MetaMask screenshots — won't break on UI updates)
- Full walkthrough: MetaMask install, add Base network, get USDC, export private key
- Covers complete crypto-newcomer path

#### API Reference
- Moderate depth: parameter table + one example per tool
- Code examples: conversational style ("Ask your AI agent: 'Take a screenshot of example.com'")
- API page layout: Claude's discretion (single page vs per-tool)

#### Getting Started Flow
- Example progression: free mode (screenshot of example.com) → paid mode (crypto sentiment for BTC)
- Troubleshooting: inline "Common Issues" section at bottom of Getting Started (not separate page)
- Common issues to cover: npx without -y, @x402/fetch vs x402-fetch, insufficient USDC, Node version

### Claude's Discretion
- Docs tone calibration (sharp for reference, approachable for tutorials)
- API reference layout (single page vs per-tool pages)
- Homepage hero layout and spacing
- Starlight sidebar navigation structure
- Exact Starlight configuration and theme customization approach

### Deferred Ideas (OUT OF SCOPE)
- Changelog / "What's New" page — skip for v1, add when there's version history to track
- Interactive API playground — v2 requirement (DEV-01)
- Real MetaMask screenshots — using placeholder images for now, consider updating post-launch

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SITE-01 | Hero section with one-liner pitch and value proposition | UX: Hero.astro component pattern with headline, tagline, value prop bullets, and dual CTA buttons. STACK: custom `src/pages/index.astro` as standalone Astro page bypassing Starlight chrome. |
| SITE-02 | Pricing table showing all tools with per-call costs | UX: data-driven `PricingTable.astro` with typed `Tool[]` array, `PricingSummary.astro` for homepage condensed view. PITFALLS: pricing drift risk — add sync comments + grep check to prevent stale pricing. |
| SITE-03 | "How it works" section explaining x402 payment flow | UX: `HowItWorks.astro` landing component; brand decision is one-liner on homepage ("HTTP 402 → USDC payment → API response. That's the whole protocol.") with detail in docs if needed. |
| SITE-04 | OG meta tags for link sharing | PITFALLS: OG URLs must be absolute — use `new URL('/og.png', Astro.site).href` or `${Astro.site}/og-image.png`. STACK: `site:` field required in `astro.config.mjs`; use `process.env.SITE_URL` as env var. UX: complete OG meta tag set including `og:image:width`, `og:image:height`, `twitter:card`. |
| DOCS-01 | Getting started guide with free mode and paid mode paths | UX: Starlight Steps + Tabs (syncKey="mcp-client") + Aside components; free mode path first, paid mode second; inline Common Issues section at bottom. MDX pattern fully documented. |
| DOCS-02 | API reference for all 6 MCP tools (params, returns, examples) | UX: single-page reference with one section per tool — parameter Markdown table + one conversational example each. Layout at Claude's discretion (single page recommended for small tool count). |
| DOCS-03 | Claude/MCP config example (copy-pasteable JSON) | UX: Tabs component with `syncKey="mcp-client"` syncing all four client configs (Claude Desktop, Claude Code, Cursor, Windsurf) across the page. PITFALLS: every `npx` invocation must include `-y`. |
| DOCS-04 | Wallet setup guide (Base network, USDC funding) | UX: Steps component with placeholder images in `site/src/assets/wallet/`. Covers MetaMask install → Base network → USDC funding → private key export. Frontmatter `lastUpdated` field for maintenance tracking. |
| DEPLOY-01 | Astro site builds to static output | STACK: `output: 'static'` explicit in `astro.config.mjs`. Build command: `cd site && npm run build` → `site/dist/`. PITFALLS: verify `site/dist/` contains no `_server/` or `_functions/` directory post-build. |

</phase_requirements>

---

## Standard Stack

### Core Dependencies (`site/package.json`)

| Library | Version | Purpose |
|---------|---------|---------|
| `astro` | `^5.18.0` (pin to 5 — do NOT install 6.x) | Framework — static site generation, file routing, layouts |
| `@astrojs/starlight` | `^0.37.7` | Docs site integration — sidebar, Pagefind search, Expressive Code, i18n, Markdown → pages |

**Critical version advisory:** Astro 6.0.0 released 2026-03-10 (today). `npm create astro@latest` will scaffold with Astro 6. Starlight 0.37.7 requires `astro ^5.5.0`. Explicitly pin `"astro": "^5.18.0"` in `site/package.json`. Upgrade only after Starlight releases explicit Astro 6 peer support (expected as Starlight 0.38.x).

### OG Image

For a single static card, place a pre-generated `og-image.png` in `site/public/`. This is simpler and more reliable than a build-time pipeline. If per-page dynamic OG images are needed in the future, use satori + sharp (see Code Examples).

### Batteries Included — No Extra Dependencies

| Feature | What Starlight Provides | Config |
|---------|------------------------|--------|
| Full-text search | Pagefind (static) | Zero config — enabled by default |
| Syntax-highlighted code blocks | Expressive Code | Zero config — copy button, line numbers, theming included |
| Static output | Astro default | `output: 'static'` explicit; no adapter required |

### Fonts

Use Google Fonts via `<link>` tags injected through Starlight's `head:` config array. Self-host `.woff2` files (downloaded from `google-webfonts-helper.herokuapp.com`) in `site/public/fonts/` with `@font-face` + `font-display: swap` if GDPR compliance or Lighthouse performance scores matter. For Phase 3, the `<link>` approach is adequate and simpler.

Two fonts: **Space Grotesk** (headlines, marketing, UI) and **JetBrains Mono** (code, pricing, endpoints).

### `site/package.json`

```json
{
  "name": "x402-site",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview"
  },
  "dependencies": {
    "@astrojs/starlight": "^0.37.7",
    "astro": "^5.18.0"
  }
}
```

This package is completely isolated from the root `package.json`. No workspace setup required. The root package does not reference `site/` at all.

### Installation

```bash
mkdir site && cd site
npm init -y
npm install astro@^5.18.0 @astrojs/starlight@^0.37.7
```

---

## Architecture Patterns

### Site Directory Structure

```
site/
├── astro.config.mjs           # Single source of truth for Astro + Starlight config
├── package.json               # site-only deps — isolated from root
├── public/
│   ├── logo-mark.png          # Mark only — copied from ~/Desktop/NanoBananaImages/
│   ├── logo-lockup.png        # Full lockup
│   ├── favicon.ico
│   ├── og-image.png           # Pre-generated static OG card (1200x630)
│   └── fonts/                 # Self-hosted .woff2 files (optional — if not using CDN)
│       ├── SpaceGrotesk-Regular.woff2
│       └── JetBrainsMono-Regular.woff2
└── src/
    ├── content.config.ts      # Content collections — docsLoader + docsSchema (root-level)
    ├── content/
    │   └── docs/              # All .md/.mdx doc pages → Starlight routes
    │       ├── getting-started.mdx
    │       ├── wallet-setup.mdx
    │       └── api-reference.mdx
    ├── pages/
    │   ├── index.astro        # Fully custom landing page — NO Starlight chrome
    │   └── pricing.astro      # Fully custom pricing detail page
    ├── components/
    │   ├── landing/
    │   │   ├── Hero.astro
    │   │   ├── HowItWorks.astro
    │   │   ├── PricingSummary.astro
    │   │   └── Footer.astro
    │   ├── pricing/
    │   │   └── PricingTable.astro
    │   └── ForceDarkTheme.astro   # ThemeProvider override — locks dark mode
    │   └── EmptyComponent.astro  # ThemeSelect override — removes toggle
    └── styles/
        ├── global.css         # --x402-* brand tokens + minimal resets
        └── starlight.css      # --sl-* variable overrides for Starlight theming
```

**Key routing rule:** Do NOT create `src/content/docs/index.md` or `index.mdx`. The custom homepage lives exclusively in `src/pages/index.astro`. If Starlight needs a docs landing, use a redirect or put it at `/docs/` — not at `/`.

### Dual CSS Layer Pattern

Two CSS files, two namespaces, no collision:

1. `global.css` — defines `--x402-*` brand tokens + minimal body/box-sizing resets. Imported directly in `src/pages/index.astro` and `pricing.astro`.
2. `starlight.css` — maps `--x402-*` values onto `--sl-color-*` and `--sl-font-*` variables. Loaded only via `customCss` in `astro.config.mjs` (applies to Starlight pages).

Both files are registered in `customCss` so Starlight loads them for doc pages. The landing page imports `global.css` directly; Astro's scoped `<style>` blocks handle component-specific styles.

### Dark Mode Enforcement

Override both Starlight components to force dark mode without flash:

```astro
<!-- src/components/ForceDarkTheme.astro -->
---
---
<script is:inline>
  document.documentElement.dataset.theme = 'dark';
</script>
```

```astro
<!-- src/components/EmptyComponent.astro -->
---
---
```

`is:inline` is mandatory — it makes the script run synchronously before first paint, eliminating FOLIOM (Flash of Light Mode). A bundled script runs too late.

Also set `data-theme="dark"` on the `<html>` element in `src/pages/index.astro` and `pricing.astro` since those pages don't use the Starlight ThemeProvider.

### Content Collection Setup

```typescript
// src/content.config.ts (root-level — NOT src/content/config.ts)
import { defineCollection } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema(),
  }),
};
```

Use `src/content.config.ts` (root-level), not `src/content/config.ts` (deprecated path).

### Sidebar Navigation

Manual sidebar definition is appropriate for this doc set (3-4 pages total):

```javascript
sidebar: [
  {
    label: 'Getting Started',
    items: [
      { slug: 'getting-started' },
      { slug: 'wallet-setup' },
    ],
  },
  {
    label: 'Reference',
    items: [
      { slug: 'api-reference' },
    ],
  },
],
```

Autogenerate is better for large, growing doc sets. Manual gives explicit order control without frontmatter `order:` overrides.

### Pricing Component Pattern

Data-driven with typed interface:

```astro
---
interface Tool {
  name: string;
  endpoint: string;
  priceUsd: string;
  priceCrypto: string;
  description: string;
  params: { name: string; type: string; required: boolean }[];
  freeMode: boolean;
}

const tools: Tool[] = [ /* ... */ ];
---
```

Prices and endpoints render in `JetBrains Mono`; tool names and descriptions in `Space Grotesk` (brand pairing rule: "Space Grotesk speaks to humans. JetBrains Mono speaks to machines.").

Homepage shows `PricingSummary` (one sentence + link to pricing page). Full `PricingTable` lives at `/pricing`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syntax-highlighted code blocks | Custom Prism/highlight.js setup | Starlight's built-in Expressive Code | Already included; copy button, line numbers, theming — zero config |
| Sitemap generation | Manually writing `sitemap.xml` | `@astrojs/sitemap` integration | Handles dynamic routes, respects `site:`, excludes excluded paths |
| OG image generation pipeline | Custom canvas/Puppeteer script, or over-engineered satori pipeline | Pre-generated static `og-image.png` placed in `site/public/` | For a single static card, a pre-made image is simpler and more reliable than a build-time pipeline |
| Dark mode enforcement via CSS only | `prefers-color-scheme` media query overrides | `ForceDarkTheme.astro` component with `is:inline` script | CSS-only approaches cannot prevent flash-of-light-mode; the inline script runs synchronously before paint |
| Font loading with `@fontsource` npm packages | Installing `@fontsource/space-grotesk` etc. | Google Fonts `<link>` via Starlight `head:` OR self-hosted `.woff2` with `@font-face` | CDN approach is simpler for 2 fonts; self-host if GDPR or Lighthouse scores matter |
| Docs search | Custom search index or Algolia setup | Starlight's built-in Pagefind | Static full-text search, zero config, no API key |

---

## Common Pitfalls

### [CRITICAL] Astro 6.0 Released Today — Pin Astro 5

**Source:** STACK

`npm create astro@latest` now scaffolds with Astro 6.0.0. Starlight 0.37.7 requires `astro ^5.5.0`. Installing Astro 6 will break Starlight with peer dependency errors.

**Avoid:** Explicitly set `"astro": "^5.18.0"` in `site/package.json`. Do not upgrade until Starlight releases Astro 6 peer support (not yet shipped as of 2026-03-10).

**Warning signs:** Peer dependency errors at install mentioning `astro` version mismatch.

---

### [CRITICAL] `npx` Without `-y` Breaks MCP stdio Transport

**Source:** PITFALLS (confirmed HIGH), UX

Any code example showing `npx x402-mcp-server` without `-y` will break end users. `npx` without `-y` writes an interactive confirmation prompt to stdout, which is the MCP stdio transport channel. The MCP client reads that prompt as malformed JSON and fails.

**Avoid:** Every `npx` invocation referencing the server must be `npx -y x402-mcp-server`. Pre-build verification: `grep -r "npx x402-mcp-server" site/src/` must return no results without `-y`. Add an `<Aside type="caution">` in Getting Started.

**Warning signs:** User reports "MCP server fails to start" immediately after copy-pasting config.

---

### [HIGH] Flash of Light Mode (FOLIOM) on Starlight Pages

**Source:** PITFALLS, STACK

Without the `ForceDarkTheme` override, Starlight's ThemeProvider runs client-side and can show a white flash before dark mode applies. CSS-only `prefers-color-scheme` overrides don't prevent this.

**Avoid:** Override `ThemeProvider` with `ForceDarkTheme.astro` using `is:inline` (synchronous, before first paint). Override `ThemeSelect` with `EmptyComponent.astro` (removes toggle).

**Note:** This is a workaround, not a first-class config option. Starlight Issue #398 tracks an official `disableThemeToggle` option. Pin Starlight and test this pattern after upgrades.

---

### [HIGH] Route Conflict: Custom Homepage vs. Starlight Index

**Source:** STACK, PITFALLS

If `src/content/docs/index.md` exists alongside `src/pages/index.astro`, Astro may throw a route collision error or silently let `src/pages/` win (priority order). Either way the behavior is undefined.

**Avoid:** Do NOT create `src/content/docs/index.md` or `index.mdx`. The custom homepage is the only route at `/`. All Starlight docs start at `/getting-started`, `/api-reference`, etc.

**Warning signs:** Build error "Route conflict detected for `/`"; or `dist/index.html` contains Starlight chrome instead of custom homepage.

---

### [HIGH] CSS Variable Override Namespaces Must Not Be Mixed

**Source:** STACK, PITFALLS, UX — all three dimensions agree

Starlight reads `--sl-color-*` variables; it ignores `--x402-*` tokens. Defining brand tokens as `--x402-*` and applying them directly to Starlight UI does nothing.

**Avoid:** Define brand tokens as `--x402-*` in `global.css`. Map them onto `--sl-color-*` in `starlight.css` via `customCss`. Keep the two namespaces separate. See Code Examples for complete mapping.

**Warning signs:** Brand colors appear on the custom landing page but Starlight sidebar/header ignore them.

---

### [HIGH] CSS Specificity: Starlight's Cascade Layer (v0.34+)

**Source:** PITFALLS

Starlight v0.34+ uses a `starlight` CSS cascade layer for built-in styles. Unlayered custom CSS in `customCss` wins automatically — no `!important` needed. On older versions, ordering was manual.

**Avoid:** Confirm Starlight 0.37.7 (already specified). If custom CSS still loses, check for Astro-scoped component styles (higher specificity) — override those with `!important` or a component override.

**Warning signs:** CSS variables in `customCss` have no visual effect; DevTools shows `.sl-*` rules winning.

---

### [HIGH] Starlight Global CSS Bleeds Into Custom `src/pages/`

**Source:** PITFALLS

Starlight's integration injects CSS globally — Expressive Code styles, font resets — across ALL pages, including `src/pages/index.astro`. This is tracked as Starlight Issue #2815 (open).

**Avoid:** Accept and exploit this rather than fighting it. Since `--sl-*` variables load everywhere, define `--x402-*` tokens as overrides on top of them. Use Astro scoped `<style>` blocks (which add `data-astro-cid-*` hashing) for landing-page-specific layouts.

---

### [HIGH] OG Image URLs Must Be Absolute

**Source:** PITFALLS, UX, STACK — all three dimensions agree

`<meta property="og:image" content="/og-image.png">` is invalid. Social crawlers (Twitter/X, Discord, Slack, LinkedIn) require fully-qualified absolute URLs and silently drop relative ones.

**Avoid:** Always construct OG URLs as `${Astro.site}/og-image.png` or `new URL('/og-image.png', Astro.site).href`. This requires `site:` to be set in `astro.config.mjs`. See Pitfall below for `site:` placeholder handling.

**Warning signs:** Discord/Slack link previews show no image; no build errors.

---

### [HIGH] `site:` Field — Use Env Var to Avoid Localhost in Production

**Source:** PITFALLS, STACK, UX — all three dimensions flag this

The home server domain/IP is an open question (STATE.md). If `site:` is set to a placeholder like `http://localhost:4321` and forgotten, all canonical URLs and OG image URLs will be wrong in the production build.

**Avoid:** Use an environment variable:

```javascript
// astro.config.mjs
site: process.env.SITE_URL || 'https://x402.todo',
```

Document setting `SITE_URL` as a required pre-build step in Phase 4. The Phase 3 build will have `og:image` pointing at `https://x402.todo/og-image.png` — harmless during dev, fixable with one env var at deploy time.

---

### [HIGH] Pricing Drift Between `src/index.ts` and Site Content

**Source:** PITFALLS

Prices are hardcoded in both the MCP server source and the brand site's pricing table. When pricing changes, both locations must be updated.

**Avoid:** Add inline sync comments: `// SYNC: matches site/src/content/docs/api-reference.mdx`. Before launch, grep to confirm all prices match. STATE.md already documents this risk and defers a shared `pricing.ts` constant to when a third API is added or pricing changes.

---

### [MEDIUM] Satori Requires Local Font Files (if dynamic OG images are used)

**Source:** UX, STACK

If the satori + sharp pipeline is used for dynamic OG images: satori renders in Node.js with no browser to fetch CDN fonts. Google Fonts URLs do not work. Satori also does not resolve CSS `var()` — hardcode hex values.

**Avoid:** Store `.ttf` files in `public/fonts/`. Use `fs.readFile()` to load them as Buffer before calling `satori()`. Document hardcoded hex values with comments referencing the brand token name.

---

### [MEDIUM] Tabs Without `syncKey` Breaks Multi-Client Docs Examples

**Source:** UX

The four MCP client config tabs (Claude Desktop, Claude Code, Cursor, Windsurf) appear in multiple places. Without `syncKey`, reader's choice in step 2 does not carry to step 4.

**Avoid:** Apply `syncKey="mcp-client"` to every `<Tabs>` group showing MCP client configs. Starlight persists the selection in `sessionStorage` across page navigation.

---

## Code Examples

### `astro.config.mjs` — Complete Scaffold

```javascript
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  output: 'static',  // explicit — don't rely on default

  // Use env var — must be set to real URL before Phase 4 deploy
  site: process.env.SITE_URL || 'https://x402.todo',

  integrations: [
    starlight({
      title: 'x402',
      description: 'The API marketplace for the AI agent economy.',

      // Dark mode only
      components: {
        ThemeProvider: './src/components/ForceDarkTheme.astro',
        ThemeSelect: './src/components/EmptyComponent.astro',
      },

      // Brand theming
      customCss: [
        './src/styles/global.css',
        './src/styles/starlight.css',
      ],

      // Google Fonts via <link>
      head: [
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'preconnect',
            href: 'https://fonts.gstatic.com',
            crossorigin: true,
          },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'stylesheet',
            href: 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap',
          },
        },
        // Global OG fallback (per-page overrides via frontmatter head field)
        {
          tag: 'meta',
          attrs: { property: 'og:image', content: `${process.env.SITE_URL || 'https://x402.todo'}/og-image.png` },
        },
        {
          tag: 'meta',
          attrs: { name: 'twitter:card', content: 'summary_large_image' },
        },
      ],

      // Manual sidebar for small doc set
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { slug: 'getting-started' },
            { slug: 'wallet-setup' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { slug: 'api-reference' },
          ],
        },
      ],
    }),
  ],
});
```

### `src/styles/global.css` — Brand Tokens

```css
/* Brand CSS tokens — source of truth. See assets/brand-guidelines.md */
:root {
  --x402-green: #4ADE80;
  --x402-green-muted: #22C55E;
  --x402-green-dim: #166534;
  --x402-green-glow: rgba(74, 222, 128, 0.15);
  --x402-bg: #000000;
  --x402-surface: #111111;
  --x402-elevated: #1A1A1A;
  --x402-border: #2A2A2A;
  --x402-text: #FFFFFF;
  --x402-text-muted: #A1A1AA;
  --x402-text-dim: #52525B;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  background-color: var(--x402-bg);
  color: var(--x402-text);
  margin: 0;
}
```

### `src/styles/starlight.css` — Starlight Variable Overrides

```css
/* Map x402 brand tokens to Starlight's theming layer */
/* Full --sl-* reference: github.com/withastro/starlight/blob/main/packages/starlight/style/props.css */
:root {
  /* Accent (links, active states, highlights) */
  --sl-color-accent-low: var(--x402-green-dim);
  --sl-color-accent: var(--x402-green);
  --sl-color-accent-high: #86EFAC;

  /* Backgrounds */
  --sl-color-bg: var(--x402-bg);
  --sl-color-bg-nav: var(--x402-surface);
  --sl-color-bg-sidebar: var(--x402-surface);

  /* Text */
  --sl-color-white: var(--x402-text);
  --sl-color-gray-1: var(--x402-text);
  --sl-color-gray-2: var(--x402-text-muted);
  --sl-color-gray-3: var(--x402-text-dim);
  --sl-color-gray-4: var(--x402-border);
  --sl-color-gray-5: var(--x402-surface);
  --sl-color-gray-6: var(--x402-bg);
  --sl-color-black: var(--x402-bg);

  /* Typography */
  --sl-font: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;
  --sl-font-system-mono: 'JetBrains Mono', ui-monospace, monospace;
}
```

### `src/pages/index.astro` — Custom Landing Page

```astro
---
import Hero from '../components/landing/Hero.astro';
import HowItWorks from '../components/landing/HowItWorks.astro';
import PricingSummary from '../components/landing/PricingSummary.astro';
import Footer from '../components/landing/Footer.astro';
import '../styles/global.css';

const siteUrl = import.meta.env.SITE_URL || 'https://x402.todo';
---

<!doctype html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />
    <title>x402 Network — The API Marketplace for AI Agents</title>
    <meta name="description" content="Pay $0.01 in USDC on Base. Get a screenshot. One HTTP request." />
    <meta property="og:title" content="x402 Network" />
    <meta property="og:description" content="The API marketplace for the AI agent economy." />
    <meta property="og:image" content={`${siteUrl}/og-image.png`} />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:image" content={`${siteUrl}/og-image.png`} />
    <link rel="icon" type="image/png" href="/logo-mark.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" />
  </head>
  <body>
    <Hero />
    <HowItWorks />
    <PricingSummary />
    <Footer />
  </body>
</html>
```

### MDX Getting Started — Tabs + Steps Pattern

```mdx
import { Tabs, TabItem, Steps, Aside } from '@astrojs/starlight/components';

## Quick Start — Free Mode

No wallet required. Screenshot tool works immediately.

<Steps>
1. Install the server:

   ```bash
   npx -y x402-mcp-server
   ```

2. Add to your MCP client config:

   <Tabs syncKey="mcp-client">
     <TabItem label="Claude Desktop">
       ```json
       {
         "mcpServers": {
           "x402": {
             "command": "npx",
             "args": ["-y", "x402-mcp-server"]
           }
         }
       }
       ```
     </TabItem>
     <TabItem label="Claude Code">
       ```bash
       claude mcp add x402 npx -y x402-mcp-server
       ```
     </TabItem>
     <TabItem label="Cursor">
       ```json
       {
         "mcpServers": {
           "x402": {
             "command": "npx",
             "args": ["-y", "x402-mcp-server"]
           }
         }
       }
       ```
     </TabItem>
     <TabItem label="Windsurf">
       ```json
       {
         "mcpServers": {
           "x402": {
             "command": "npx",
             "args": ["-y", "x402-mcp-server"]
           }
         }
       }
       ```
     </TabItem>
   </Tabs>

3. Ask your AI agent:

   > "Take a screenshot of example.com"

   Your agent calls `take_screenshot` automatically. No payment required in free mode.
</Steps>

<Aside type="caution" title="Always use -y">
  Run `npx -y x402-mcp-server`, not `npx x402-mcp-server`. Without `-y`, npx
  prompts for confirmation — which breaks MCP's stdio transport.
</Aside>
```

### API Reference Per-Tool Pattern

```mdx
## take_screenshot

Captures a full-page PNG of a public URL.

**Cost:** $0.01 USDC on Base | Free in free mode

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | `string` | Yes | Public URL to capture |
| `full_page` | `boolean` | No | Capture full scrollable page (default: `false`) |

**Example:**

> "Take a screenshot of stripe.com's pricing page"

```json
{
  "tool": "take_screenshot",
  "arguments": {
    "url": "https://stripe.com/pricing",
    "full_page": true
  }
}
```
```

### Pre-Build Verification Script

Run before every `astro build`:

```bash
# 1. Verify no bare npx in docs
if grep -r "npx x402-mcp-server" site/src/ | grep -v "\-y"; then
  echo "ERROR: Found npx without -y in docs"
  exit 1
fi

# 2. Verify static output mode
if ! grep -q "output.*static" site/astro.config.mjs; then
  echo "WARN: output: 'static' not explicit in astro.config.mjs"
fi

# 3. Verify site/ dist has no SSR artifacts
if [ -d site/dist/_server ] || [ -d site/dist/_functions ]; then
  echo "ERROR: SSR output detected in site/dist/ — expected static"
  exit 1
fi
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `src/content/config.ts` | `src/content.config.ts` (root-level) | Required; old path deprecated |
| `defineCollection` with manual schema | `docsLoader()` + `docsSchema()` from Starlight | Required pattern for Starlight content layer |
| `@fontsource/*` npm packages | Google Fonts `<link>` in `head:` OR self-hosted `.woff2` | Both work; `<link>` simpler for 2-font projects |
| Astro 4 adapters for static hosting | No adapter — `output: 'static'` is default | Explicit declaration recommended |
| Manual OG image or Puppeteer-based generation | Pre-generated static `og.png` OR satori + sharp endpoint | Static file simpler for single card |
| Both light and dark Starlight themes | Component override (ForceDarkTheme + EmptyComponent) | Dark-only enforcement without FOLIOM |
| Astro 6.x | Astro 5.18.x (required while Starlight awaits Astro 6 support) | Pin explicitly; upgrade path tracked on Starlight GitHub |

**Deprecated / avoid:**
- `src/content/config.ts` — use `src/content.config.ts`
- `@astrojs/starlight` < 0.30 — content layer API changed significantly
- `astro@6.x` — do not install until Starlight explicitly supports it
- CSS-only dark mode enforcement — cannot prevent FOLIOM

---

## Open Questions

1. **`SITE_URL` / domain for `site:` in `astro.config.mjs`** — Home server IP/subdomain not yet resolved (STATE.md open question). Using `process.env.SITE_URL` as the env var pattern means Phase 4 sets the value at deploy time with no code change.

2. **API reference layout** — Single page vs. per-tool pages (Claude's discretion per CONTEXT.md). Research recommendation: single page for the current 6-tool set. Per-tool pages make sense when tool count grows or when tools have enough parameters to warrant dedicated pages with their own TOC entries.

3. **Astro 6 upgrade timing** — Watch Starlight GitHub releases for `0.38.x` declaring `astro ^6.0.0` peer support. Migration should be straightforward once Starlight ships it.

4. **Self-hosted fonts vs. Google Fonts CDN** — Deferred for v1. If Lighthouse or GDPR becomes a concern, download Space Grotesk and JetBrains Mono `.woff2` files and switch to `@font-face` + `font-display: swap` with no CDN request.

5. **Pricing sync mechanism** — Sync comments + pre-launch grep check are sufficient for v1. If pricing changes frequently, consider extracting a shared `pricing.json` that both `src/index.ts` and the site content read from.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on stack (Astro 5 + Starlight 0.37.7), theming approach (dual CSS layer), dark mode enforcement (component override), and OG image handling (static file). One minor conflict resolved: STACK recommended a single `custom.css` file; UX recommended separate `global.css` + `starlight.css`. Adopted UX's two-file approach as it prevents namespace collision more clearly. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Optional sections present: User Constraints, Phase Requirements, State of the Art, Open Questions. |
| Dimension Coverage | PASS | STACK: version advisory, scaffold structure, config reference, content.config.ts, CSS variable mapping all integrated. UX: component structure, landing/pricing patterns, satori OG endpoint, MDX content patterns, sidebar config all integrated. PITFALLS: all 10 pitfalls integrated; Don't Hand-Roll table merged and expanded. |
| Requirement Coverage | PASS | All 9 Phase 3 requirements (SITE-01 through SITE-04, DOCS-01 through DOCS-04, DEPLOY-01) mapped to findings with specific research support cited. |

---

## Sources

### Primary (HIGH confidence)

- https://starlight.astro.build/getting-started/ — scaffold command, project structure
- https://starlight.astro.build/manual-setup/ — `content.config.ts` exact syntax, `docsLoader`, `docsSchema`
- https://starlight.astro.build/reference/configuration/ — all config options including `components`, `customCss`, `head`, `sidebar`
- https://starlight.astro.build/guides/css-and-tailwind/ — `--sl-color-*` variables, `:root[data-theme='dark']` override syntax, `customCss` config
- https://starlight.astro.build/guides/pages/ — custom pages in `src/pages/` alongside Starlight docs
- https://starlight.astro.build/guides/sidebar/ — `autogenerate`, manual `items`, frontmatter `order`/`label`
- https://starlight.astro.build/guides/authoring-content/ — MDX features, Expressive Code, frontmatter
- https://starlight.astro.build/components/steps/ — Steps component MDX usage
- https://starlight.astro.build/components/asides/ — Aside component variants
- https://starlight.astro.build/components/tabs/ — Tabs/TabItem, `syncKey` behavior
- https://starlight.astro.build/reference/overrides/ — `ThemeProvider`, `ThemeSelect` override pattern
- https://starlight.astro.build/reference/frontmatter/ — frontmatter fields including `tableOfContents`, `lastUpdated`
- https://docs.astro.build/en/reference/configuration-reference/ — `output`, `site`, `base`, `build.outDir`
- https://docs.astro.build/en/guides/styling/ — scoped styles, `is:global`, `define:vars`, import CSS
- https://docs.astro.build/en/guides/fonts/ — self-hosting fonts guidance
- https://github.com/withastro/starlight/blob/main/packages/starlight/style/props.css — full `--sl-*` variable list
- https://github.com/withastro/astro/releases — confirmed Astro 6.0.0 released 2026-03-10
- https://github.com/withastro/starlight/releases — confirmed Starlight 0.37.7 is latest, requires `astro >= 5.16.9`
- [STATE.md known risks section] — `npx -y`, SSR output, pricing sync, site URL (project-internal source)

### Secondary (MEDIUM confidence)

- https://starlight.astro.build/guides/overriding-components/ — component override mechanics
- https://github.com/withastro/starlight/discussions/949 — ForceDarkTheme workaround (community-verified)
- https://github.com/withastro/starlight/discussions/1048 — cascade layer ordering
- https://github.com/withastro/starlight/issues/2815 — styles bleed into non-Starlight routes (January 2025)
- https://github.com/withastro/starlight/issues/1080 — route conflict pattern
- https://mahadk.com/posts/astro-og-with-satori — satori + sharp Astro endpoint pattern
- https://arne.me/blog/static-og-images-in-astro/ — static site OG endpoint with `prerender = true`
- https://hideoo.dev/notes/starlight-og-images/ — `astro-og-canvas` endpoint pattern
- https://lirantal.com/blog/getting-social-media-previews-right-with-opengraph-meta-tags — OG absolute URL requirement

### Tertiary (LOW confidence)

- https://lexingtonthemes.com/tutorials/how-to-create-interactive-pricing-table-astro-tailwind-alpine/ — pricing table data pattern (Alpine.js-specific, adapted)
- https://github.com/withastro/starlight/issues/398 — official `disableThemeToggle` option (status may have changed)
- Web search results confirming Astro 6 support PR in Starlight repo — exact release date unknown

---

## Metadata

**Confidence breakdown:**
- STACK: HIGH (official docs verified; Astro 6 version advisory flagged)
- UX: HIGH (official Starlight docs verified; satori pattern from community guides)
- PITFALLS: HIGH (core pitfalls verified via official docs and GitHub issues; route collision at MEDIUM)

**Research date:** 2026-03-10
**Valid until:** 2026-06-01 (re-verify Starlight version and Astro 6 support status)
**Dimensions researched:** STACK, UX, PITFALLS (3 of 3 returned)
