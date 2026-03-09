# Pitfalls Research

**Domain:** npm publishing + Astro brand/docs site for an MCP server with crypto wallet integration
**Researched:** 2026-03-09
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Publishing Private Key to npm via Missing `files` Whitelist

**What goes wrong:**
Running `npm publish` without an explicit `files` field in `package.json` ships the entire repository to the public registry. This includes `.env` files, `.planning/`, `src/`, `openapi/`, and any file that isn't explicitly gitignored at the moment of publish. Because this project uses `X402_PRIVATE_KEY` as an env var — and because developers often have a `.env` in the project root during development — a single missing `files` field could result in a Base wallet private key on the public npm registry. npm does not allow full unpublish of packages after 72 hours.

**Why it happens:**
npm's default behavior (no `files` field, no `.npmignore`) is to include everything not in `.gitignore`. Developers who haven't published before assume gitignore is sufficient protection. It isn't — `.env` is typically gitignored, which protects git, but `npm publish` reads the filesystem, not git's index.

**How to avoid:**
Add `"files": ["dist", "README.md", "LICENSE"]` to `package.json` before any publish attempt. Then run `npm pack --dry-run` and inspect the output — it lists every file that would be included in the tarball. This must happen in Phase 1 (package hardening), before the first `npm publish`.

**Warning signs:**
- `package.json` has no `files` field (current state — confirmed missing)
- No `.npmignore` exists as a fallback
- A `.env` file exists at project root with secrets
- `npm pack --dry-run` output includes `src/`, `.planning/`, or any non-`dist` directory

**Phase to address:**
Phase 1 (npm publish prep) — must be the very first task, before any other publish-related work.

---

### Pitfall 2: Shebang Missing from Compiled Output — Silent `npx` Failure

**What goes wrong:**
The `src/index.ts` file has `#!/usr/bin/env node` as its first line. TypeScript's `tsc` compiler strips this during compilation. The resulting `dist/index.js` starts without the shebang, which means MCP clients invoking `npx x402-mcp-server` get a subprocess that doesn't execute as a Node script in all environments — or worse, fails silently because the MCP client treats the startup error as a transport failure rather than surfacing it.

**Why it happens:**
TypeScript treats comments as directives to strip. The `#!` line looks like a comment to `tsc` even though it's a POSIX shell directive. This is a well-known gotcha for CLI packages compiled with `tsc`, but it's easy to miss if you don't test the built artifact directly.

**How to avoid:**
After every `tsc` build, verify `dist/index.js` starts with `#!/usr/bin/env node`. Add a `postbuild` script that injects the shebang if missing:
```json
"postbuild": "node -e \"const fs=require('fs');const f='dist/index.js';const c=fs.readFileSync(f,'utf8');if(!c.startsWith('#!/usr/bin/env node'))fs.writeFileSync(f,'#!/usr/bin/env node\\n'+c);\""
```
Then run `npx x402-mcp-server` locally from the published package (or via `npm link`) before declaring success.

**Warning signs:**
- `head -1 dist/index.js` does not output `#!/usr/bin/env node`
- `npx x402-mcp-server` exits immediately with no output
- MCP client shows "server disconnected" immediately after startup
- `npm link` + invocation produces a permission or execution error

**Phase to address:**
Phase 1 (npm publish prep) — verify shebang preservation as part of the build verification checklist before first publish.

---

### Pitfall 3: Publishing Broken Package Exports — `publint` Catches What `npm pack` Misses

**What goes wrong:**
The `main`, `bin`, and `exports` fields in `package.json` can point to files that exist in the dev environment but are malformed, have wrong paths, or have wrong module format for the declared `"type": "module"`. A broken package can install correctly (npm downloads the tarball fine) but fail to execute, producing cryptic Node errors like "Cannot use import statement in a module" or "ERR_MODULE_NOT_FOUND" that look like user configuration problems.

**Why it happens:**
`npm pack --dry-run` only lists files. It doesn't validate that `main`, `exports`, or `bin` paths resolve correctly, or that ESM/CJS format matches `"type": "module"`. Since this package is `"type": "module"` (ESM), any tooling that injects CJS-style code (e.g., a postbuild script using `require()`) will break.

**How to avoid:**
Run `npx publint` in the project root before publishing. It validates that all `package.json` export fields resolve to real files with the correct module format. Zero config, fast. Make it a mandatory step before `npm publish`. Also check that `tsconfig.json` has `"module": "NodeNext"` or `"module": "ESNext"` to ensure ESM output.

**Warning signs:**
- `publint` reports errors about missing exports or format mismatches
- `node dist/index.js` works but `npx x402-mcp-server` fails differently
- TypeScript's `moduleResolution` is `bundler` or `node` (not `NodeNext`) — this can produce paths that work locally but fail when installed via npm

**Phase to address:**
Phase 1 (npm publish prep) — add `publint` check to the pre-publish checklist.

---

### Pitfall 4: Using `@x402/fetch` Instead of `x402-fetch` in Docs

**What goes wrong:**
The brand/docs site Getting Started guide will include install instructions for x402 dependencies. The scoped package `@x402/fetch` exists on npm but is a placeholder stub — it does nothing. The working package is the unscoped `x402-fetch` (v1.1.0). If the docs site's "how to set up your own x402 integration" section references the wrong package name, any developer following along will have a non-functional setup with no clear error message.

**Why it happens:**
The scoped naming convention (`@x402/fetch`) looks like the "official" package — scoped packages under an org name appear more authoritative. Developers copying examples from other x402 resources may encounter both names and assume they're equivalent.

**How to avoid:**
In all brand site documentation: use `x402-fetch` (unscoped). Add an explicit callout box in the docs: "Note: Use `x402-fetch`, not `@x402/fetch` — the scoped package is a placeholder." This constraint is already documented in PROJECT.md; it must also be surfaced in the brand site itself.

**Warning signs:**
- Any docs page or README snippet showing `npm install @x402/fetch`
- Any code example importing from `@x402/fetch`
- Docs pulled from upstream x402 protocol resources that haven't updated their package references

**Phase to address:**
Phase 2 (brand site content) — add a content review checklist item specifically for this package name.

---

### Pitfall 5: Coin Parameter Path Traversal via Missing Regex Validation

**What goes wrong:**
The `x402_sentiment` and `x402_intelligence` tools construct URL paths using `params.coin.toLowerCase()` without validation. An agent (or a malicious prompt injection) could pass `coin: "../admin"` or `coin: "btc?override=1&admin=true"` as the coin parameter. This would produce requests to `/sentiment/../admin` or `/sentiment/btc?override=1&admin=true`, potentially hitting unintended endpoints on the Railway backend.

**Why it happens:**
The current Zod schema for `coin` is `z.string()` with no regex constraint. Zod's `.string()` accepts any string, including path separators and query string characters. The Railway APIs are the actual defense layer, but defense in depth is required — especially in an automated payment system.

**How to avoid:**
Add `.regex(/^[A-Z0-9]{1,10}$/)` to the coin parameter schema (after `.toUpperCase()` normalization, or use a `.transform()` + `.regex()` chain):
```typescript
coin: z.string()
  .min(1).max(10)
  .regex(/^[A-Za-z0-9]+$/, "Coin symbol must be alphanumeric only")
  .transform(s => s.toUpperCase())
```
Similarly, the `url` parameter in `x402_screenshot` and `pdf_url` in `x402_pdf_extract` should use `.url()` validation to prevent non-HTTP URLs like `file://`, `javascript:`, or internal network URLs.

**Warning signs:**
- `coin` schema is `z.string()` with no further constraints (current state — confirmed in `src/index.ts`)
- `url` and `pdf_url` schemas are `z.string()` with no `.url()` validation (current state)
- Any tool that interpolates user input directly into URL path segments

**Phase to address:**
Phase 1 (npm publish prep) — security hardening must happen before the package is publicly available. These are pre-publish code changes.

---

### Pitfall 6: Astro Site Output Mode Set to SSR — Breaks Self-Hosting

**What goes wrong:**
Some Astro scaffolding commands or documentation examples set `output: 'server'` in `astro.config.mjs`, which enables server-side rendering. This requires a Node.js runtime process on the home server (via an Astro adapter like `@astrojs/node`). Running `rsync site/dist/` to nginx's static file directory will produce a directory that doesn't actually serve pages — it outputs a server entrypoint, not static HTML files.

**Why it happens:**
Astro 5 changed the default output mode to `'static'` for new projects, but Starlight's scaffold or older templates may set `output: 'server'`. The error only manifests after deploy, not during local `npm run dev` (dev server always works regardless of output mode).

**How to avoid:**
Explicitly set `output: 'static'` in `astro.config.mjs` — do not leave it implicit, even though static is the default. This makes the intent clear and prevents accidental override. Verify after `npm run build` that `site/dist/` contains `index.html` files, not a `server/` directory.

**Warning signs:**
- `site/dist/` contains a `server/` subdirectory after build instead of flat HTML files
- `astro.config.mjs` has `output: 'server'` or `output: 'hybrid'`
- Build output size is tiny (a few KB of JS) rather than full HTML pages

**Phase to address:**
Phase 2 (Astro site scaffold) — verify output mode in the scaffolding step before writing any content.

---

### Pitfall 7: `site/` Directory Accidentally Published to npm

**What goes wrong:**
If the brand site is scaffolded in `site/` (subdirectory of the repo root) before the `files` whitelist is properly set, and then `npm publish` runs from the repo root, the entire `site/` directory (Astro source, `node_modules`, build output) gets included in the npm tarball. This is not a security issue (no secrets in the site) but it inflates the package size from ~50KB to potentially 100MB+ (Astro + all its dependencies), making `npm install x402-mcp-server` unusably slow.

**Why it happens:**
The `site/` directory's own `node_modules/` is not covered by the root `.gitignore` unless explicitly added. Without a `files` whitelist in the root `package.json`, npm walks the entire directory tree.

**How to avoid:**
The `files` whitelist (`["dist", "README.md", "LICENSE"]`) is the correct fix — it prevents everything outside `dist/` from shipping. This is the same fix as Pitfall 1. The ordering matters: set `files` whitelist BEFORE scaffolding `site/`. Run `npm pack --dry-run` after scaffolding to confirm `site/` does not appear in the output.

**Warning signs:**
- `npm pack --dry-run` output includes any `site/` paths
- Package size (shown by `npm pack`) exceeds 1MB
- `npm publish` takes more than a few seconds to prepare the tarball

**Phase to address:**
Phase 1 (npm publish prep) — `files` whitelist must be in place before the `site/` directory is created.

---

### Pitfall 8: `.planning/` Contents Exposed via npm or Site

**What goes wrong:**
The `.planning/` directory contains internal research, state, and decision documents. This is not a security risk per se, but it's internal project scaffolding that should never be visible to package consumers or brand site visitors. Without the `files` whitelist, it ships to npm. If the brand site is accidentally configured to serve from the repo root rather than `site/dist/`, `.planning/` could be browsable on the web server.

**Why it happens:**
nginx misconfiguration — pointing the document root at the repo root instead of `site/dist/`. This is a common first-deploy mistake when the path is set by hand.

**How to avoid:**
For npm: covered by the `files` whitelist. For the web server: verify the nginx document root is `/var/www/x402-api-network/` (or equivalent), not the repo checkout path. Use `rsync site/dist/` (not `rsync ./`) to deploy only the static build output.

**Warning signs:**
- Visiting `https://yourdomain.com/.planning/` returns a directory listing or 200 response
- nginx `root` directive points to the git repo checkout directory
- `rsync` deploy command does not include `site/dist/` as the source

**Phase to address:**
Phase 3 (deploy) — verify nginx document root at deploy time.

---

### Pitfall 9: Pricing Drift Between `src/index.ts` and Brand Site

**What goes wrong:**
Tool descriptions in `src/index.ts` hardcode prices (`$0.01 USDC per capture`, `$0.05 USDC per query`, `$0.10 USDC per query`). The brand site will also display these prices. When prices change in a future version, there are now two places to update. If only the MCP server is updated and the brand site is not, users read incorrect pricing on the site and agents see different pricing in tool descriptions — a trust-breaking inconsistency in a pay-per-use product.

**Why it happens:**
At MVP scale (one dev, one site, one server), duplication is the pragmatic choice — extracting a shared pricing constants file requires build tooling coordination between two separate packages. The problem is invisible at first because both are updated together, then a patch release happens quickly and the site gets skipped.

**How to avoid:**
Accept the duplication at v1.0 but document it explicitly. In each pricing line in `src/index.ts`, add a comment: `// SYNC: update site/src/content/pricing.md if this changes`. In the brand site pricing table, add a comment linking back to `src/index.ts`. When the project has more than one contributor or more frequent releases, extract to a shared `pricing.ts` constant file that both the MCP server and the Astro build can import.

**Warning signs:**
- Price in `src/index.ts` tool description does not match price in brand site pricing table
- A git commit updates `src/index.ts` prices but no `site/` files are changed in the same commit
- No comment in `src/index.ts` pointing to the site as a sync target

**Phase to address:**
Phase 2 (brand site content) — add sync comments when writing the pricing content. Accept duplication; make it explicit.

---

### Pitfall 10: npx Prompt Breaks MCP stdio Transport

**What goes wrong:**
When an agent or developer configures the MCP server without the `-y` flag (`"command": "npx", "args": ["x402-mcp-server"]`), npx may prompt "Need to install x402-mcp-server@1.0.0. Ok to proceed? (y)" before launching the server. The MCP client is expecting JSON-formatted MCP protocol messages on stdio. Instead, it receives this interactive prompt. Most MCP clients interpret the unexpected input as a protocol error and disconnect. The user sees "Server failed to initialize" with no explanation.

**Why it happens:**
The `-y` flag is not obvious to developers configuring MCP servers manually. Most documented examples show the bare `npx package-name` form. npx added the prompt as a security feature in npm 7+, and many developers haven't internalized that it's a problem for non-interactive subprocess invocations.

**How to avoid:**
Every code snippet in the README and brand site that shows MCP client config MUST use `npx -y x402-mcp-server`. No exceptions. Add a callout in the Getting Started guide: "The `-y` flag is required — without it, npx will prompt for confirmation and the MCP client will fail to connect." Consider also documenting `npm install -g x402-mcp-server` followed by `x402-mcp-server` as an alternative for users who want to avoid `npx` entirely.

**Warning signs:**
- Any README or docs snippet showing `"args": ["x402-mcp-server"]` without `-y`
- Bug reports of "server disconnects immediately" from new users
- The example Claude Desktop config JSON missing the `-y` arg

**Phase to address:**
Phase 1 (README update) and Phase 2 (brand site docs) — every config snippet must include `-y`.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded prices in both `src/index.ts` and brand site | No build tooling coordination needed at MVP | Price drift creates trust issues in a pay-per-use product; two places to update on every pricing change | MVP only — add sync mechanism or shared constant after v1.0 |
| All 6 tools in a single `src/index.ts` | Simple to read and deploy; no module system complexity | File exceeds 400 lines; hard to test individual tools; adding new tools increases cognitive load linearly | Acceptable through ~10 tools; extract `src/tools/` when adding a fourth API |
| No `prepublishOnly` script running tests | Faster publish workflow | Publishes broken package if a code change breaks the server without catching it in CI | Never acceptable — add `prepublishOnly` build check at minimum; add type check too |
| Manual `rsync` deploy for brand site | Zero CI/CD setup; fast to implement | Manual deploys get skipped; site drifts from latest docs; no deploy history | MVP only — add a `make deploy` or deploy script early to reduce friction |
| Accepting `any` type for x402/viem interop | Bypasses TypeScript generics friction with x402-fetch | Type errors from viem API changes will surface at runtime instead of compile time | Acceptable while x402-fetch types are unstable; revisit when x402-fetch publishes stable types |
| No LICENSE file (currently missing) | Nothing | npm warns on publish; package feels unmaintained; downstream users can't legally use the package | Never acceptable — create `LICENSE` file before first publish |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| npm registry | Running `npm publish` without `--dry-run` verification | Always run `npm pack --dry-run` and `npx publint` first; review the file list; only then publish |
| npm registry | Publishing without an npm account login | Run `npm whoami` before publish; `npm login` if not authenticated; use `--access public` for first publish of unscoped package |
| npm registry | Not tagging the git commit before publish | Tag `v1.0.0` in git before running `npm publish`; the published version and the git tag must match |
| x402-fetch | Importing from `@x402/fetch` (scoped stub) | Use `x402-fetch` (unscoped, v1.1.0) — already correct in `package.json` and `src/index.ts`; guard against regressions |
| viem + x402-fetch | Passing a typed `WalletClient` to `wrapFetchWithPayment` | Use `as any` interop cast as currently implemented — viem's generics don't align perfectly; don't attempt to fix this with type gymnastics |
| Railway APIs | Assuming Railway URLs are stable across deploys | Hardcoded Railway URLs in `src/index.ts` are correct for now; if a Railway service is redeployed with a new name, all three URL constants need updating |
| Home server nginx | Setting `root` to git repo directory instead of `site/dist/` | nginx `root` must point to the rsync'd static output directory only; verify with a curl before calling deploy done |
| Home server nginx | Missing MIME type for `.mjs` or `.astro` files | Astro static output is HTML/CSS/JS only — standard nginx MIME types cover everything; no custom MIME config needed |
| Astro + Starlight | Installing `@astrojs/tailwind` (deprecated) | Use `@tailwindcss/vite` Vite plugin for Tailwind v4; `@astrojs/tailwind` only works with Tailwind v3 |
| MCP clients | Configuring `command: "node"` + `args: ["dist/index.js"]` with a local path | After npm publish, all configs should use `command: "npx", args: ["-y", "x402-mcp-server"]`; document migration from local path |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `x402_network_info` performs 3 parallel health checks on every call | Tool takes 5+ seconds when any Railway service is slow; health checks add latency to every tool listing | Add a short timeout (already uses `AbortSignal.timeout(5000)`) — confirmed in code; acceptable at current scale | Breaks UX at any call frequency if Railway services have cold starts |
| Single monolithic `src/index.ts` for all tools | Hard to add new tools; no separation between tool logic and transport | Extract to `src/tools/` after adding a fourth API | Acceptable through ~10 tools; 6 tools is fine |
| Static pricing on brand site with no cache headers | Not a performance trap — pricing is static | Not applicable | N/A |
| No CDN in front of home server docs site | Slow international loads; single point of failure for docs | Accept for MVP; add Cloudflare proxy (free tier) if traffic materializes | Matters at 10k+ monthly visits or if home server has downtime |
| No start-time verification that private key is valid | Agent starts working, first paid tool call fails on malformed key | Add `privateKeyToAccount(PRIVATE_KEY)` check at startup rather than lazy initialization (current: lazy via `getPaidFetch()`) | Breaks on first paid call; confusing error message points to payment, not config |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Missing `files` whitelist before publish | Private key in `.env` ships to npm registry; wallet is drained | `"files": ["dist", "README.md", "LICENSE"]` in `package.json` — highest priority action |
| Unvalidated `coin` parameter in URL path | Path traversal to unintended Railway API endpoints; potential for parameter injection in payment flows | `z.string().regex(/^[A-Za-z0-9]+$/).max(10)` on `coin` params |
| Unvalidated `url` and `pdf_url` parameters | SSRF to internal network addresses; `file://` URI access on Railway; `javascript:` URI injection | `.url()` validator on all URL parameters in Zod schemas |
| Wallet private key logged in error messages | If any catch block logs `err` objects that contain wallet state, the key could appear in MCP client logs | Confirm current error paths only log `err.message`, never the full error object or wallet client state |
| npm account with weak password or no 2FA | Package hijacking — attacker publishes malicious version; all agent installs auto-update | Enable npm 2FA before first publish; use `npm publish --otp` |
| Brand site served over HTTP (not HTTPS) | Docs site config snippets (env var instructions) seen by network observers; trust signal failure | nginx + Let's Encrypt TLS; or Cloudflare proxy in front of HTTP home server |
| Payment cap bypass via rapid parallel calls | An agent loop calling paid tools faster than the cap is enforced could exceed intended spend | `BigInt(100000)` cap is per-call, not per-session — document this clearly; consider documenting wallet balance monitoring |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Docs show only the paid workflow | Developers without a Base wallet can't get started; high drop-off | Lead with free mode; show the full free-to-paid progression in Getting Started |
| Claude config JSON shows local file path instead of npx | Users who read Getting Started during development copy the dev config; their agents fail after they close the local server | Always show npm-installed config in "production" examples; put local dev config in a separate "dev" section |
| Tool descriptions don't mention payment will occur | Agents make paid calls without agent or user awareness; erodes trust in pay-per-use model | Every tool description already mentions price and payment mode — this is handled; maintain it in any future tools |
| Error messages say "X402_PRIVATE_KEY not configured" for free test calls | Free test calls don't require a key; the error message implies the key is always required | Current code routes correctly (free vs. paid); confirm error only surfaces for paid-only endpoints when key is missing |
| Brand site has no copy-pasteable npx install command | Developers who want to try immediately must mentally reconstruct the install command | Hero section must include a code block: `npx -y x402-mcp-server` — one click to copy |
| Docs use `$0.01 USDC` without explaining Base network | Web3-naive developers don't know what "USDC on Base" means or how to fund a wallet | Getting Started guide must include a one-paragraph explainer: Base is L2 Ethereum, USDC is a stablecoin, funding requires a MetaMask-compatible wallet |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **npm publish:** `npm publish` ran and returned success — verify package is actually installable: `npm install -g x402-mcp-server && x402-mcp-server` from a clean machine or temp directory
- [ ] **Shebang preserved:** TypeScript compiled `dist/index.js` — verify `head -1 dist/index.js` shows `#!/usr/bin/env node`, not `"use strict"` or blank
- [ ] **`files` whitelist set:** `package.json` has `files` field — verify with `npm pack --dry-run` that only `dist/`, `README.md`, `LICENSE` appear, not `src/` or `.planning/`
- [ ] **LICENSE file exists:** `LICENSE` declared in `files` field — verify the actual `LICENSE` file exists in the repo root (currently missing)
- [ ] **Zod validation hardened:** `coin` and `url` inputs validated — verify `z.string().regex(...)` and `.url()` are in place in `src/index.ts` before publish
- [ ] **Brand site is static output:** Astro built successfully — verify `site/dist/` contains `index.html`, not a `server/` directory with a Node entrypoint
- [ ] **nginx serving correct path:** Site deployed via rsync — verify document root is `site/dist/` content, not the repo root; visit `/.planning/` on the live domain and confirm 404
- [ ] **npx `-y` flag in all snippets:** Docs and README written — grep for `"npx"` in all doc files and confirm every occurrence is `npx -y`, no exceptions
- [ ] **`@x402/fetch` not referenced anywhere:** Brand site content written — grep for `@x402/fetch` in all docs; it must not appear
- [ ] **Free mode tested post-publish:** Package published — test `x402_screenshot` with a test domain in free mode (no key) from the installed npm package to confirm routing works
- [ ] **npm 2FA enabled:** Account configured — confirm `npm profile get` shows `tfa.mode` is not `disabled`

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Private key published to npm | HIGH | 1. Immediately rotate the wallet: transfer all USDC/ETH to a new wallet, generate new key. 2. `npm deprecate x402-mcp-server@1.0.0 "Security: rotate X402_PRIVATE_KEY immediately"`. 3. Publish `1.0.1` with the file removed. 4. Cannot fully unpublish after 72h — deprecation is the best available action. |
| Broken package published (missing shebang, bad exports) | LOW | 1. Fix the issue locally. 2. Bump version to `1.0.1`. 3. `npm publish`. 4. Deprecate the broken version: `npm deprecate x402-mcp-server@1.0.0 "Use 1.0.1 — fixes startup issue"` |
| Wrong package name (`@x402/fetch`) in published docs | LOW | 1. Edit brand site content. 2. Rebuild and redeploy via rsync. 3. Update README on npm (publish new version with corrected README). |
| Brand site serving wrong directory (nginx misconfiguration) | LOW | 1. SSH to home server. 2. Fix nginx `root` directive. 3. `nginx -t && systemctl reload nginx`. Total time: 5 minutes. |
| Astro site built in SSR mode (no static files) | LOW | 1. Add `output: 'static'` to `astro.config.mjs`. 2. `npm run build` in `site/`. 3. Re-rsync. |
| Pricing drift (site shows wrong price) | MEDIUM | 1. Identify which is authoritative (the MCP server's tool description or the brand site). 2. Update the lagging copy. 3. If both changed, decide canonical price and update both. 4. Add sync comment to prevent recurrence. |
| npm account compromised (malicious publish) | HIGH | 1. Contact npm support immediately. 2. Rotate npm credentials. 3. Deprecate any versions published without authorization. 4. Publish clean version. 5. Enable 2FA if not already enabled. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Missing `files` whitelist (secrets in npm) | Phase 1: package hardening | `npm pack --dry-run` shows only `dist/`, `README.md`, `LICENSE` |
| Missing shebang in `dist/index.js` | Phase 1: package hardening | `head -1 dist/index.js` shows `#!/usr/bin/env node` |
| Broken exports (no `publint`) | Phase 1: package hardening | `npx publint` exits with no errors |
| Missing LICENSE file | Phase 1: package hardening | `ls LICENSE` exists in repo root |
| Unvalidated `coin` / `url` inputs | Phase 1: security hardening | Zod schemas include `.regex()` and `.url()` constraints |
| `@x402/fetch` confusion | Phase 1: README + Phase 2: brand site | `grep -r "@x402/fetch" .` returns no matches in docs |
| Astro SSR mode (not static) | Phase 2: Astro scaffold | `site/dist/` contains `index.html` after build |
| `site/` published to npm | Phase 1: `files` whitelist (prerequisite to Phase 2) | `npm pack --dry-run` shows no `site/` paths after scaffold |
| `.planning/` exposed on web | Phase 3: deploy verification | `curl https://yourdomain.com/.planning/` returns 404 |
| Pricing drift | Phase 2: brand site content | Sync comments in `src/index.ts` and `site/` pricing content |
| npx without `-y` in docs | Phase 1: README + Phase 2: brand site | `grep -rn '"npx"' README.md site/` — every match includes `-y` |
| npx prompt breaking stdio | Phase 1: README + Phase 2: brand site | Same as above — `-y` flag in all config snippets |
| npm 2FA not enabled | Phase 1: pre-publish security | `npm profile get` shows 2FA enabled before first publish |

---

## Sources

- Existing codebase: `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — confirmed `coin` and `url` are unvalidated `z.string()`, confirmed `files` field missing from `package.json`
- npm security: https://snyk.io/blog/best-practices-create-modern-npm-package/ — files field, .npmignore, publish verification
- npm CLI docs: https://docs.npmjs.com/cli/v10/configuring-npm/package-json#files — `files` field behavior
- MCP server publish patterns: https://aihero.dev/publish-your-mcp-server-to-npm — shebang, bin, npx `-y` requirement
- publint: https://publint.dev/ — export field validation rules
- Astro rendering modes: https://docs.astro.build/en/basics/rendering-modes/ — static vs server output
- x402-fetch package: confirmed non-scoped `x402-fetch` v1.1.0 is correct; `@x402/fetch` is a stub (observed during STACK.md research)
- Architecture research: `.planning/research/ARCHITECTURE.md` — anti-patterns 1–4 cross-referenced
- Features research: `.planning/research/FEATURES.md` — MVP definition and anti-features cross-referenced

---
*Pitfalls research for: npm publishing + Astro brand/docs site for x402 MCP server with crypto wallet*
*Researched: 2026-03-09*
