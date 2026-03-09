# Stack Research

**Domain:** npm publishing + Astro brand/docs site for an MCP server package
**Researched:** 2026-03-09
**Confidence:** HIGH

## Context

The MCP server is already built and working (TypeScript, ESM, `@modelcontextprotocol/sdk ^1.11.0`, `viem ^2.0.0`, `x402-fetch ^1.1.0`). This research covers ONLY what's needed to add:

1. A publishable, well-formed npm package (the MCP server itself)
2. An Astro brand + docs site, self-hosted as static output

No new runtime dependencies are needed for the MCP server. All additions are either `package.json` config changes, dev tools, or the separate brand site.

---

## Part 1: npm Publishing

### package.json Changes Required

The current `package.json` is missing several fields required for a properly published npm package.

**Add:**
- `files` — explicit allowlist to prevent leaking source, `.env`, `.planning`, etc.
- `engines` — signal Node version requirement
- `prepublishOnly` — auto-build before publish
- `repository`, `homepage`, `bugs` — registry metadata
- `author` — attribution

**Existing `bin` entry is correct.** The `dist/index.js` file must have `#!/usr/bin/env node` as its first line — TypeScript's compiled output doesn't add this automatically. Verify after `tsc` build.

**`files` field recommendation:**
```json
"files": ["dist", "README.md", "LICENSE"]
```

This explicitly excludes: `src/`, `.planning/`, `node_modules/`, `.env*`, `tsconfig.json`.

**`prepublishOnly` script:**
```json
"prepublishOnly": "npm run build"
```

Runs TypeScript compilation automatically before `npm publish`.

### Dev Tools for Publishing

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| `publint` | `^0.3.18` | Validate package exports before publishing | Catches mismatches between `package.json` fields and actual `dist/` output — prevents publishing a broken package |

**Run before every publish:**
```bash
npx publint
```

Validates `main`, `exports`, `bin` fields match what's in `dist/`. Zero config.

### Shebang Requirement

TypeScript's `tsc` does NOT preserve `#!/usr/bin/env node` in compiled output. The source file `src/index.ts` already has this line at top. Verify `dist/index.js` starts with it after build. If not, add a postbuild script:

```json
"postbuild": "node -e \"const fs=require('fs');const f='dist/index.js';const c=fs.readFileSync(f,'utf8');if(!c.startsWith('#!/usr/bin/env node'))fs.writeFileSync(f,'#!/usr/bin/env node\\n'+c);\""
```

### Security Checklist (No New Packages)

- `X402_PRIVATE_KEY` is env-only — confirmed in current code, nothing to add
- `.npmignore` is optional since `files` field takes precedence when both exist — use `files`, not `.npmignore`
- Run `npm pack --dry-run` before first publish to audit exact file list

---

## Part 2: Astro Brand + Docs Site

The brand site is a **separate project** — it does not live inside `x402-mcp-server/`. Suggested location: `~/projects/x402-brand-site/` or a `site/` subdirectory at the repo root.

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `astro` | `^5.18.0` | Static site framework | Latest stable (5.18.0, released Feb 2026); generates pure static HTML+CSS+JS with zero JS by default; deploys as a file drop to any web server; no Node runtime needed on home server |
| `@astrojs/starlight` | `^0.37.6` | Documentation theme | Official Astro docs theme — includes search, nav, code highlighting, dark mode, mobile-responsive; zero config for a docs site; pairs naturally with Astro 5 |

**Choose one path:**

**Path A — Marketing + Docs combined (Starlight):**
Use Starlight as the base. It handles docs pages natively and supports custom landing page components. Good if the docs ARE the primary pitch. Most MCP server registries link directly to docs.

**Path B — Marketing-first (plain Astro + Tailwind):**
Custom Astro site for the brand pitch, with `/docs` section as Markdown pages. More design control. More work.

**Recommendation: Path A (Starlight).** The target audience is developers. Starlight's built-in search, code highlighting, and nav are immediately useful. A custom landing page component can handle the marketing pitch above the docs fold.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tailwindcss` | `^4.0.0` | Utility CSS | Only for Path B (custom design) or if Starlight's default design needs significant customization. Tailwind v4 uses a Vite plugin — no `@astrojs/tailwind` integration needed |
| `@tailwindcss/vite` | `^4.0.0` | Vite plugin for Tailwind v4 | Replaces old `@astrojs/tailwind` for Tailwind v4; add to Astro's vite plugins config |
| `@astrojs/mdx` | `^4.x` | MDX support | Only if you need JSX components inside Markdown docs. Not needed for plain `.md` docs — Astro handles those natively |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `astro` CLI | `npx astro dev` for local preview, `npx astro build` for static output | No global install needed; use via npx or npm scripts |
| `astro check` | TypeScript/Astro type checking | Run in CI before deploy |

### Installation (Path A — Starlight)

```bash
# Create site (separate project)
npm create astro@latest -- --template starlight

# Or manually
npm install astro @astrojs/starlight

# Dev
npm run dev

# Build (outputs to dist/)
npm run build
```

### Installation (Path B — Custom Astro + Tailwind)

```bash
npm create astro@latest

# Add Tailwind v4
npm install tailwindcss @tailwindcss/vite

# Optional MDX
npx astro add mdx
```

### Astro Config for Static Output (Self-Hosting)

```js
// astro.config.mjs
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  output: 'static',   // default — generates file-based HTML
  integrations: [
    starlight({
      title: 'x402 API Network',
      // ...
    }),
  ],
});
```

`output: 'static'` is the default. The `dist/` folder is self-contained — copy to `/var/www/` and serve with Nginx.

### Self-Hosting Deployment

No additional npm packages needed. Build generates a static `dist/` folder. Deploy with:

```bash
npm run build
rsync -av dist/ user@homeserver:/var/www/x402-api-network/
```

Nginx config: standard static file serving. No Node runtime required on the server.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Astro 5 | Next.js | When you need SSR, API routes, or a React-heavy UI — overkill for static docs/marketing |
| Astro 5 | VitePress | VitePress is Vue-only and docs-only; Astro handles both marketing and docs in one site |
| Astro 5 | Docusaurus | Good alternative if the site is docs-only and React ecosystem is preferred; heavier bundle |
| Starlight | Custom Astro + Tailwind | When brand design requires full visual control; more work, same deployment model |
| `publint` | Manual testing only | `publint` catches export field errors that `npm pack --dry-run` misses |
| `files` field | `.npmignore` | `.npmignore` works but `files` is explicit allowlist, harder to accidentally leak files |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@astrojs/tailwind` (old integration) | Deprecated for Tailwind v4; only works with Tailwind v3 | `@tailwindcss/vite` Vite plugin |
| `@x402/fetch` (scoped package) | Placeholder stub, non-functional | `x402-fetch` (non-scoped, v1.1.0) — already in use |
| Global `npm install -g astro` | Astro must be installed locally per project | `npm install astro` as devDependency |
| Astro SSR output mode | Requires Node runtime on home server; breaks static deployment | `output: 'static'` (default) |
| `.npmignore` alongside `files` field | `files` takes precedence — `.npmignore` is ignored when `files` exists; having both is confusing | Use only `files` |

## Stack Patterns by Variant

**If the brand site is docs-heavy (primary goal = developer adoption):**
- Use Starlight — built-in search, nav, versioning, code highlighting
- Add a custom landing page component at the root route for the marketing pitch
- Zero additional styling libraries needed

**If the brand site is marketing-heavy (primary goal = conversion/splash page):**
- Use plain Astro with Tailwind v4
- Write docs as Markdown content collections under `src/content/docs/`
- More design work but full visual control

**If publishing to npm before the brand site is live:**
- `homepage` field in package.json can point to the future URL
- Publish works without the site being live
- The `README.md` becomes the npm registry page — prioritize it

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `astro@^5.18.0` | Node.js >= 18.17.1, 20.3.0, or >= 22 | Astro 5 dropped Node 16 support |
| `@astrojs/starlight@^0.37.6` | `astro@^5.x` | Starlight 0.37.x requires Astro 5; do not use with Astro 4 |
| `tailwindcss@^4.0.0` + `@tailwindcss/vite` | `astro@^5.2.0+` | Astro 5.2 added native Vite plugin support; old `@astrojs/tailwind` integration is Tailwind v3 only |
| `publint@^0.3.18` | Any npm package | Dev tool only, no peer dependency constraints |

## Sources

- [npmjs.com/package/astro](https://www.npmjs.com/package/astro) — confirmed v5.18.0 latest stable
- [npmjs.com/package/@astrojs/starlight](https://www.npmjs.com/package/@astrojs/starlight) — confirmed v0.37.6 latest
- [npmjs.com/package/publint](https://www.npmjs.com/package/publint) — confirmed v0.3.18 latest
- [astro.build/blog/astro-520](https://astro.build/blog/astro-520/) — Tailwind v4 Vite plugin support in Astro 5.2
- [tailwindcss.com/docs/installation/framework-guides/astro](https://tailwindcss.com/docs/installation/framework-guides/astro) — Tailwind v4 install with `@tailwindcss/vite`
- [docs.astro.build/en/guides/deploy/](https://docs.astro.build/en/guides/deploy/) — static output + self-hosting
- [aihero.dev/publish-your-mcp-server-to-npm](https://www.aihero.dev/publish-your-mcp-server-to-npm) — MCP server npm publish pattern (shebang, bin, files)
- [snyk.io/blog/best-practices-create-modern-npm-package](https://snyk.io/blog/best-practices-create-modern-npm-package/) — npm package security best practices
- [publint.dev](https://publint.dev/) — publint validation rules

---
*Stack research for: x402 API Network — npm publishing + Astro brand/docs site*
*Researched: 2026-03-09*
