# Project Research Summary

**Project:** x402 API Network — MCP Server npm Publishing + Astro Brand/Docs Site
**Domain:** npm package publishing + static documentation site for an MCP server with pay-per-use crypto wallet integration
**Researched:** 2026-03-09
**Confidence:** HIGH

## Executive Summary

The x402 MCP server is already built and functional. This research covers the two remaining work streams: publishing the server as a proper npm package and building a developer-facing brand/docs site using Astro. Both are well-understood problem domains with established patterns — the primary risk is not architectural complexity but pre-publish hygiene mistakes, specifically the absence of a `files` whitelist in `package.json` that could leak `.env` secrets (including `X402_PRIVATE_KEY`) to the public npm registry. This must be the first action taken, before any other work begins.

The recommended approach is a two-phase delivery: harden the npm package and publish first, then scaffold the Astro brand site as a `site/` subdirectory in the same repo. Keeping both in one repository prevents documentation drift — a real concern in a pay-per-use product where pricing inconsistencies break user trust. The Astro static site deploys via rsync to a home server with nginx, requiring no additional runtime infrastructure.

The most important differentiators — free test mode, single env var setup, per-call payment cap, and self-describing `x402_network_info` tool — are all already implemented. The research confirms the build work is primarily packaging and documentation, not new features.

## Key Findings

### Recommended Stack

The MCP server needs no new runtime dependencies. Package hardening requires only `package.json` config changes (`files`, `engines`, `prepublishOnly`, `repository`, `author`) plus a `postbuild` script to guard the shebang. The single dev tool addition is `publint` (run via `npx publint` before every publish) to validate that `main`, `exports`, and `bin` fields in `package.json` resolve correctly against the compiled `dist/` output — catching export mismatches that `npm pack --dry-run` misses.

For the brand/docs site, Astro 5 with Starlight is the clear choice. Starlight is the official Astro docs theme — it provides built-in search, nav, code highlighting, dark mode, and mobile response at zero configuration cost. The target audience is developers, and Starlight's default layout serves that audience better than a custom marketing build. A custom landing page component above the docs fold handles the marketing pitch. Tailwind is only needed if Starlight's design requires significant customization; skip it for v1.

**Core technologies:**
- `astro@^5.18.0` — static site framework — generates pure HTML/CSS/JS, zero runtime on home server, self-hosting via `rsync` to nginx
- `@astrojs/starlight@^0.37.6` — docs theme — search, nav, dark mode, code highlighting, mobile-responsive, zero config
- `publint@^0.3.18` — npm pre-publish validation — catches export field mismatches before they reach the registry
- `@tailwindcss/vite` (optional) — Tailwind v4 Vite plugin — only if Starlight customization is needed; do NOT use the deprecated `@astrojs/tailwind`

### Expected Features

**Must have (table stakes — launch blockers):**
- `files` whitelist (`["dist", "README.md", "LICENSE"]`) in `package.json` — prevents source/secrets leakage to npm
- `#!/usr/bin/env node` shebang preserved in `dist/index.js` — required for `npx` invocation to work
- `LICENSE` file (MIT) at repo root — npm warns without it; downstream users can't legally use the package
- `engines: {"node": ">=18"}` in `package.json` — sets runtime expectation for MCP clients
- Updated README with `npx -y x402-mcp-server` install instructions and Claude config JSON
- `npm publish` after `npm pack --dry-run` and `npx publint` verification
- Brand site hero with one-sentence value prop
- Tool listing table with names, descriptions, and prices
- Getting Started guide: install → configure → free mode → paid mode
- Free vs. paid comparison table — lowers wallet barrier, reduces drop-off
- Copy-pasteable Claude config JSON with `-y` flag
- Basic OG/meta tags and dark mode layout

**Should have (competitive differentiators — add when possible):**
- "How x402 works" sequence diagram — x402 is not widely known; a visual makes the payment flow click
- API reference pages rendered from existing `openapi/` specs
- GitHub releases + `CHANGELOG.md` linked from site footer
- Uptime/status indicator (lightweight, not dynamic polling)

**Defer (v2+):**
- Developer dashboard / account system — Phase 3 per existing PROJECT.md; needs product validation
- Interactive API playground — requires backend proxy; defer until demand signal
- CI/CD npm publish pipeline — manual publish first, add CI after workflow is stable
- Third-party API onboarding

### Architecture Approach

The repo uses a monorepo-lite structure: the MCP server package lives at the root (published to npm via the `files` whitelist), and the Astro brand site lives in `site/` with its own `package.json`. No monorepo tooling (Turborepo, nx) is needed at this scale. The two packages share the same git history but have completely separate dependency trees — consumers of `x402-mcp-server` never download Astro. The `openapi/` specs at the repo root can be referenced by the Astro build without duplication.

**Major components:**
1. Root `package.json` (hardened) — `files: ["dist", "README.md", "LICENSE"]`, `prepublishOnly: "npm run build"`, `engines`, `repository`
2. `dist/index.js` (compiled MCP server) — only artifact shipped to npm; shebang must be preserved or injected via `postbuild`
3. `site/` (Astro + Starlight) — separate package, own deps, builds to `site/dist/` (static HTML/CSS/JS), deployed via `rsync` to nginx; never enters npm bundle
4. `site/src/content/` — MDX docs for Getting Started, tool reference, pricing
5. `site/src/pages/` — Astro page routes: index (hero), docs, pricing
6. `site/public/` — favicon, OG image

### Critical Pitfalls

1. **Missing `files` whitelist before publish** — add `"files": ["dist", "README.md", "LICENSE"]` to `package.json` immediately; run `npm pack --dry-run` to verify; a `.env` with `X402_PRIVATE_KEY` at project root would ship to the public registry and cannot be fully removed after 72 hours

2. **Shebang stripped by `tsc`** — TypeScript strips `#!/usr/bin/env node` from compiled output; verify with `head -1 dist/index.js`; add a `postbuild` script that injects the shebang if missing; MCP clients silently fail with "server disconnected" when shebang is absent

3. **Unvalidated `coin` and `url` parameters (security, pre-publish)** — current Zod schemas are bare `z.string()` with no constraints; add `.regex(/^[A-Za-z0-9]+$/).max(10)` on `coin` params and `.url()` on all URL params to prevent path traversal and SSRF; this is a code change that must land before the package is publicly available

4. **`npx` without `-y` in all docs and config snippets** — npx prompts for install confirmation in npm 7+; this interactive prompt breaks MCP stdio transport; every config example in README and brand site must use `npx -y x402-mcp-server` without exception; grep all docs before shipping

5. **Astro SSR output mode breaks self-hosting** — explicitly set `output: 'static'` in `astro.config.mjs`; verify after build that `site/dist/` contains `index.html` files, not a `server/` directory; do not leave output mode implicit even though static is the Astro 5 default

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Package Hardening + Security (pre-publish blockers)
**Rationale:** Security and publish hygiene must be locked before any public artifact exists. The `files` whitelist is the highest-risk item in the entire project — a single publish without it could expose wallet secrets. Input validation (`coin`, `url`) must also be resolved before public availability.
**Delivers:** A publish-ready, hardened npm package that is safe to list publicly
**Addresses:** `files` whitelist, shebang injection, `LICENSE` file, `engines` field, Zod input validation, `publint` pre-publish check, npm 2FA
**Avoids:** Pitfalls 1 (secrets in npm), 2 (missing shebang), 3 (broken exports), 5 (path traversal/SSRF), 7 (`site/` accidentally published)

### Phase 2: README Update + npm Publish
**Rationale:** README is the npm registry page; it must be updated with npm-based install instructions before the package goes live. Publishing establishes the package name and enables the brand site to reference real install commands.
**Delivers:** `x402-mcp-server` live on npm registry with correct `npx -y` config examples
**Uses:** Hardened `package.json` from Phase 1, `publint` validation
**Implements:** `npm pack --dry-run` verification → `npm publish`
**Addresses:** Updated README, semantic versioning, git tag `v1.0.0`, `npx -y` in all snippets

### Phase 3: Astro Brand Site Scaffold + Content
**Rationale:** Brand site requires npm package to be live (can't write real install commands before publish). Astro + Starlight is the correct stack — scaffold after npm publish so Getting Started guide references the live package.
**Delivers:** Fully populated brand/docs site in `site/` with hero, tool listing, pricing, Getting Started guide, free vs. paid table
**Uses:** `astro@^5.18.0`, `@astrojs/starlight@^0.37.6`, static output mode, `site/` subdirectory structure
**Implements:** Architecture components: `site/src/pages/index.astro` (hero), `site/src/content/` (docs), `site/public/` (OG assets)
**Addresses:** Pitfalls 4 (`npx -y` in all snippets), 6 (Astro SSR mode), 9 (pricing sync comments), `@x402/fetch` package name callout

### Phase 4: Deploy to Home Server
**Rationale:** Deploy is the final verification step — confirms static output, nginx path, and TLS are all correct before calling the milestone done.
**Delivers:** Brand site live at home server domain, nginx serving `site/dist/` over HTTPS
**Addresses:** Pitfall 8 (`.planning/` exposed via nginx misconfiguration), TLS requirement, verify `curl https://yourdomain.com/.planning/` returns 404

### Phase Ordering Rationale

- Phase 1 before everything: The `files` whitelist and input validation are pre-publish blockers with no dependencies. Setting them first eliminates the highest-risk action.
- Phase 2 before Phase 3: npm publish must happen before writing real install instructions for the brand site. The Getting Started guide needs a real package name and version to reference.
- Phase 3 before Phase 4: Brand site content must be complete before deploying; partial deploys of docs sites create a worse first impression than no site at all.
- Security hardening (Zod validation) is bundled in Phase 1 rather than Phase 3: it's a code change to `src/index.ts`, not a docs change, and it must be in the published package.

### Research Flags

Phases with well-known patterns (can proceed directly to planning):
- **Phase 1:** Standard npm publish hardening — all patterns are well-documented; `publint` and `npm pack --dry-run` are deterministic checks
- **Phase 2:** `npm publish` workflow — straightforward; follow the pre-publish checklist
- **Phase 3:** Astro + Starlight scaffold — official docs are thorough; Starlight's scaffold generates a working docs site with no config
- **Phase 4:** nginx static file serving — standard; rsync + `root` directive + Let's Encrypt TLS is a solved pattern

No phases require additional research before planning. All implementation decisions are resolved.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified exact versions on npm: astro 5.18.0, starlight 0.37.6, publint 0.3.18; confirmed version compatibility matrix |
| Features | HIGH | Features derived from existing codebase + well-understood npm/docs site conventions; no speculative features |
| Architecture | HIGH | Monorepo-lite with `site/` subdirectory is a standard pattern; `files` whitelist + separate `site/package.json` is the correct boundary |
| Pitfalls | HIGH | Critical pitfalls (missing `files`, shebang, Zod validation) confirmed against actual `src/index.ts` and `package.json` — not theoretical |

**Overall confidence:** HIGH

### Gaps to Address

- **Pricing sync mechanism:** At v1.0, pricing is duplicated between `src/index.ts` and the brand site. Sync comments are the accepted mitigation. When a third API is added or pricing changes for the first time, evaluate extracting a shared `pricing.ts` constant that both packages import.
- **Domain name:** The `site` URL (`x402.network` or similar) is not yet confirmed. The `astro.config.mjs` `site:` field needs the actual domain before deploying for correct canonical URLs and OG meta tags.
- **npm account 2FA:** Must be enabled before first publish. Not researchable — requires action on the npm account directly.

## Sources

### Primary (HIGH confidence)
- [npmjs.com/package/astro](https://www.npmjs.com/package/astro) — confirmed v5.18.0 latest stable
- [npmjs.com/package/@astrojs/starlight](https://www.npmjs.com/package/@astrojs/starlight) — confirmed v0.37.6 latest
- [npmjs.com/package/publint](https://www.npmjs.com/package/publint) — confirmed v0.3.18 latest
- [docs.npmjs.com/cli/v10/configuring-npm/package-json#files](https://docs.npmjs.com/cli/v10/configuring-npm/package-json#files) — `files` field behavior
- [docs.astro.build/en/basics/rendering-modes/](https://docs.astro.build/en/basics/rendering-modes/) — static vs server output
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — confirmed coin/url schemas are unvalidated `z.string()`; confirmed shebang in source
- `/Users/jameswisdom/projects/x402-mcp-server/package.json` — confirmed `files` field missing; confirmed `bin`, `main`, `type: module` already correct

### Secondary (MEDIUM confidence)
- [aihero.dev/publish-your-mcp-server-to-npm](https://www.aihero.dev/publish-your-mcp-server-to-npm) — MCP server npm publish pattern: shebang, bin, `npx -y` requirement
- [snyk.io/blog/best-practices-create-modern-npm-package](https://snyk.io/blog/best-practices-create-modern-npm-package/) — npm package security best practices: `files` whitelist, pre-publish checklist
- [publint.dev](https://publint.dev/) — export field validation rules
- [tailwindcss.com/docs/installation/framework-guides/astro](https://tailwindcss.com/docs/installation/framework-guides/astro) — Tailwind v4 + `@tailwindcss/vite` (replaces deprecated `@astrojs/tailwind`)

### Tertiary (LOW confidence — needs validation during implementation)
- Shebang preservation behavior of `tsc`: documented in community sources; verify empirically with `head -1 dist/index.js` after first build
- Astro Starlight custom landing page component support: documented in Starlight docs but specific implementation depends on Starlight version

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
