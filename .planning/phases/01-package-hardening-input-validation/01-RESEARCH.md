# Phase 1: Package Hardening + Input Validation - Research

**Researched:** 2026-03-09
**Domain:** npm package configuration, Zod v4 input validation, TypeScript CLI packaging
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Package Contents
- npm tarball ships ONLY: `dist/index.js`, `dist/index.d.ts`, `README.md`, `LICENSE`, `package.json`
- Exclude: `openapi/`, `src/`, `.planning/`, `site/`, `tsconfig.json`, `*.tgz`
- `files` field in package.json: `["dist", "README.md", "LICENSE"]`
- Unscoped package name: `x402-mcp-server`

#### Input Validation
- Coin regex: `/^[A-Z0-9]{1,10}$/i` — alphanumeric only, 1-10 chars. Blocks path traversal. No hyphens, dots, or special chars.
- URL validation: `z.string().url()` — well-formed URLs only, any scheme. Backend handles scheme restrictions.
- Error messages: Zod defaults — no custom error messages needed for v1.

#### Repo Hygiene
- Create .gitignore (Claude's discretion on exact contents — standard Node patterns + project-specific exclusions)
- `.planning/` docs committed to git (project history, useful for future context)
- Repo will be pushed to GitHub as a public repo (matches MIT license)

#### Shebang Handling
- Postbuild npm script that checks `dist/index.js` and prepends `#!/usr/bin/env node` if tsc stripped it
- Runs automatically after every `npm run build`

#### Pre-Publish Testing
- `npm pack` to create tarball → install in temp dir → verify `npx` works and MCP server starts
- `publint` validation for package export correctness
- Manual verification only — no test framework for v1

#### npm Account
- Not currently logged in (`npm whoami` returns ENEEDAUTH)
- `npm adduser` is a Phase 2 prerequisite, not Phase 1

### Claude's Discretion

No specific requirements — open to standard approaches. The research identified the exact tools and patterns to use (publint, postbuild shebang injection, files whitelist).

### Deferred Ideas (OUT OF SCOPE)

- Automated unit tests for Zod validation schemas — could add in a future milestone if regressions become a concern
- CI/CD pipeline for automated npm publish — explicitly out of scope for v1.0
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PKG-01 | `files` whitelist in package.json limits published content to `dist/`, `README.md`, `LICENSE` | Current state confirmed dangerous: npm pack --dry-run shows .planning/, src/, openapi/, tsconfig.json ALL being published. `files` field pattern is well-established. |
| PKG-02 | `prepublishOnly` script runs `tsc` build before every publish | npm lifecycle confirmed: `prepublishOnly` runs before `npm publish` (not `npm pack`). Pattern: `"prepublishOnly": "npm run build"` |
| PKG-03 | `engines` field declares Node 18+ requirement | Standard field, trivial to add: `"engines": {"node": ">=18"}` |
| PKG-04 | LICENSE file exists on disk (MIT) | LICENSE file does NOT currently exist on disk. Must create. MIT text from choosealicense.com. |
| PKG-05 | Shebang (`#!/usr/bin/env node`) preserved in `dist/index.js` after compilation | tsc 5.9.3 DOES preserve shebang from src/index.ts. Postbuild guard still required as defensive safety net. Pattern: inline node script or separate shell script. |
| PKG-06 | `publint` validates package exports before publish | publint v0.3.18 not yet installed. Must add as devDependency. Has `BIN_FILE_NOT_EXECUTABLE` rule that validates shebang presence. Run: `npx publint` or via prepublishOnly. |
| VAL-01 | `coin` parameter validated with `/^[A-Z0-9]{1,10}$/i` regex | Currently NO validation on coin param in x402_sentiment and x402_intelligence tools. Zod v4.3.6 is installed (transitive via MCP SDK). `z.string().regex()` works correctly in v4 — verified empirically. |
| VAL-02 | `url` and `pdf_url` parameters validated with `z.string().url()` | Currently `url` and `pdf_url` use bare `z.string()` with no URL format enforcement. `z.string().url()` works correctly in Zod v4 — verified empirically. |
</phase_requirements>

## Summary

Phase 1 is pure configuration and hardening — the MCP server itself is already built and functional. The work is partitioned into two independent tracks: package metadata (package.json fields, LICENSE file, scripts) and input validation (Zod schema tightening).

The most critical finding from codebase inspection is that `npm pack --dry-run` shows the current tarball would include `.planning/`, `src/`, `openapi/`, and `tsconfig.json` — everything except what's in `.gitignore` (which excludes `node_modules/`, `dist/`, `.env`). Paradoxically, dist is excluded from git but IS needed in the tarball. The `files` whitelist is the fix: it overrides `.gitignore` for publishing and allows explicitly including `dist/`. This must be the first change made.

The validation track is clean: Zod v4.3.6 is installed (transitively via `@modelcontextprotocol/sdk`) and both `z.string().url()` and `z.string().regex()` are empirically verified to work correctly. The only action is adding `.regex(/^[A-Z0-9]{1,10}$/i)` to the `coin` parameter schemas and `.url()` to the `url` and `pdf_url` parameter schemas. Zod is NOT declared as a direct dependency — it should be added to avoid depending on a transitive dep.

**Primary recommendation:** Start with the `files` whitelist change, verify with `npm pack --dry-run`, then handle the remaining package.json changes (engines, scripts), create LICENSE, add postbuild shebang guard, install publint, then tighten validation schemas.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| zod | 4.3.6 (already in node_modules) | Runtime schema validation | Used by MCP SDK itself; z.string().url() and .regex() are the idiomatic approach |
| publint | 0.3.18 | npm package export linting | Purpose-built for catching packaging errors before publish |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| npm pack | built-in (npm 11.6.2) | Dry-run tarball preview | Run before any publish to verify included files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `files` whitelist | `.npmignore` | `.npmignore` is more fragile — easy to forget new dirs. `files` is an allowlist, safer than blocklist. |
| postbuild inline node script | `shebang-trim` npm package | Adds a dependency for a 2-line operation. Inline script is sufficient. |
| `prepublishOnly` for tsc | `prepack` | `prepack` runs on BOTH `npm pack` and `npm publish`. `prepublishOnly` runs only on publish. Either works; `prepublishOnly` is the standard choice when the goal is safety-on-publish. |

**Installation:**
```bash
npm install --save-dev publint
npm install zod  # promote from transitive to direct dependency
```

## Architecture Patterns

### Recommended Project Structure
```
x402-mcp-server/
├── dist/              # compiled output — IN tarball (via files: ["dist"])
│   ├── index.js       # shebang must be present; publint validates this
│   └── index.d.ts     # TypeScript declarations
├── src/               # source — NOT in tarball
├── .planning/         # planning docs — NOT in tarball, committed to git
├── openapi/           # API specs — NOT in tarball, committed to git
├── node_modules/      # NOT in tarball, NOT in git
├── .gitignore         # tracks: node_modules/, dist/, .env, *.tgz
├── LICENSE            # MIT — IN tarball (via files: ["LICENSE"])
├── README.md          # IN tarball (via files: ["README.md"])
├── package.json       # always IN tarball
└── tsconfig.json      # NOT in tarball (excluded by files whitelist)
```

### Pattern 1: files Whitelist in package.json
**What:** An allowlist of paths that npm includes in the published tarball. Overrides `.gitignore` for publishing.
**When to use:** Always — it is the only safe way to prevent accidental leaks.
**Example:**
```json
// package.json
{
  "files": ["dist", "README.md", "LICENSE"]
}
```
Note: `package.json` is always included regardless of `files`. `node_modules/` is always excluded. `dist/` must be listed even though it's in `.gitignore` — `files` takes precedence over `.gitignore` for publishing.

### Pattern 2: npm Lifecycle Scripts for Build Safety
**What:** `prepublishOnly` runs `tsc` automatically before `npm publish`, preventing publish of stale compiled output.
**When to use:** Any package that requires a build step before publishing.
**Example:**
```json
// package.json scripts
{
  "build": "tsc",
  "postbuild": "node -e \"const fs=require('fs'),f='dist/index.js',c=fs.readFileSync(f,'utf8');if(!c.startsWith('#!/'))fs.writeFileSync(f,'#!/usr/bin/env node\\n'+c)\"",
  "prepublishOnly": "npm run build",
  "start": "node dist/index.js"
}
```
**Lifecycle note:** `prepublishOnly` runs during `npm publish` only. It does NOT run during `npm pack`. When running `npm pack` for testing, run `npm run build` manually first.

### Pattern 3: Zod Validation on MCP Tool Parameters
**What:** Add `.regex()` or `.url()` to Zod string schemas passed to `server.tool()`.
**When to use:** Any tool parameter that accepts user-supplied strings that will be used in URL construction or API calls.
**Example:**
```typescript
// Source: zod v4 docs — verified empirically against installed v4.3.6

// VAL-01: coin parameter
coin: z
  .string()
  .regex(/^[A-Z0-9]{1,10}$/i)
  .describe("Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"),

// VAL-02: url/pdf_url parameters
url: z
  .string()
  .url()
  .describe("URL to capture (full URL including https://)"),

pdf_url: z
  .string()
  .url()
  .describe("URL of the PDF to extract text from"),
```

### Pattern 4: engines Field for Node Version Requirement
**What:** Declares minimum Node.js version in package.json. Prevents installation on incompatible systems.
**Example:**
```json
{
  "engines": {
    "node": ">=18"
  }
}
```

### Anti-Patterns to Avoid
- **Using .npmignore instead of files:** `.npmignore` is a blocklist — you must remember to add every new directory you don't want published. `files` is an allowlist — safe by default.
- **Importing zod as a transitive dependency:** `zod` is currently imported in `src/index.ts` but is NOT in `package.json` dependencies. If `@modelcontextprotocol/sdk` ever changes its zod dependency, validation breaks. Add `zod` as a direct dep.
- **Running publint without the files whitelist in place:** publint may emit `USE_FILES` suggestion. Fix the whitelist first, then run publint to catch any remaining issues.
- **Forgetting that dist/ is gitignored:** The `.gitignore` excludes `dist/`. The `files` whitelist is independent — it allows publishing `dist/` while still excluding it from git. This is correct and intentional.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verifying published package contents | Manual file listing | `npm pack --dry-run` | Shows exactly what would be in the tarball |
| Package export validation | Custom checks | `publint` | Catches ESM/CJS mismatches, missing shebang, invalid exports, missing files |
| URL format validation | Custom regex | `z.string().url()` | RFC-compliant, handles edge cases, integrates with MCP tool schema |

**Key insight:** Package publishing correctness is a well-solved domain. The tooling (publint, npm pack --dry-run) handles the verification. The only manual work is configuration.

## Common Pitfalls

### Pitfall 1: dist/ Excluded From Tarball Due to .gitignore
**What goes wrong:** The current `.gitignore` has `dist/` in it (line 2). Without a `files` field, npm uses `.gitignore` to determine what to exclude — so `dist/` would be MISSING from the published package. The package would publish but `require('x402-mcp-server')` would fail with "cannot find module".
**Why it happens:** npm falls back to `.gitignore` when no `files` field and no `.npmignore` exists.
**How to avoid:** Add `"files": ["dist", "README.md", "LICENSE"]` to package.json. The `files` field overrides `.gitignore` for publishing purposes.
**Warning signs:** `npm pack --dry-run` would not show `dist/index.js` in tarball contents.
**Current status:** CONFIRMED via `npm pack --dry-run` — dist IS currently being published (because npm 11 uses .gitignore fallback, but the files warning confirms no whitelist exists). Wait — re-reading the dry-run output: `dist/index.js` IS in the tarball output. This means npm's fallback includes dist anyway in this case. However the explicit `files` whitelist is still required to EXCLUDE the undesired files (`.planning/`, `src/`, `openapi/`, etc.).

### Pitfall 2: .planning/ and src/ Published to npm Registry
**What goes wrong:** `npm pack --dry-run` output confirms all of `.planning/`, `src/index.ts`, `openapi/`, and `tsconfig.json` would be included in the current tarball without a `files` whitelist.
**Why it happens:** npm uses `.gitignore` as fallback — which only excludes `node_modules/`, `dist/`, `.env`. Everything else is included.
**How to avoid:** Add `files` whitelist immediately as the first change in this phase.
**Warning signs:** Current `npm pack --dry-run` output explicitly shows these files being included.

### Pitfall 3: prepublishOnly Does Not Run During npm pack
**What goes wrong:** Developer runs `npm pack` to test the tarball, gets stale compiled output, mistakenly believes prepublishOnly ran.
**Why it happens:** `prepublishOnly` is designed to run only on `npm publish` (not `npm pack`). Only `prepack` runs on both.
**How to avoid:** When testing with `npm pack`, explicitly run `npm run build` first. Or use `prepack` instead of `prepublishOnly` (but the user decisions locked `prepublishOnly`).
**Warning signs:** Making code changes, running `npm pack` to test, and not seeing those changes reflected.

### Pitfall 4: Zod as Undeclared Direct Dependency
**What goes wrong:** `src/index.ts` imports `zod` directly (`import { z } from "zod"`) but `zod` is not in `package.json` dependencies — it is transitively provided by `@modelcontextprotocol/sdk`. If the SDK updates and removes or changes its zod dependency, the import breaks.
**Why it happens:** The project was set up without explicitly adding zod as a dependency.
**How to avoid:** Add `"zod": "^3.0.0"` (or match installed v4) to dependencies. Given MCP SDK uses zod v4.3.6, use `"zod": "^4.0.0"`.
**Warning signs:** `npm ls zod` shows it as a transitive dep with no direct requirer.

### Pitfall 5: publint BIN_FILE_NOT_EXECUTABLE
**What goes wrong:** publint has a rule `BIN_FILE_NOT_EXECUTABLE` that fails if a file in the `bin` field doesn't start with a shebang. Without the shebang guard, if tsc ever strips the shebang, publint would catch it — but only if publint is running.
**Why it happens:** Not all TypeScript configurations preserve shebangs (confirmed tsc 5.9.3 with module: Node16 preserves it, but other configs or future versions may not).
**How to avoid:** The postbuild shebang guard prevents the issue before publint checks it.

### Pitfall 6: MIT License Year in LICENSE File
**What goes wrong:** MIT license requires copyright year and holder name. A blank/generic LICENSE file without the author's name doesn't satisfy the license terms.
**How to avoid:** Use `Copyright (c) 2026 James Wisdom` (or just `Copyright (c) 2026 x402-mcp-server contributors`) in the LICENSE file.

## Code Examples

Verified patterns from official sources and empirical testing:

### package.json — Complete Hardened State
```json
{
  "name": "x402-mcp-server",
  "version": "1.0.0",
  "description": "MCP server for the x402 API Network — screenshot, PDF extraction, and crypto sentiment tools with USDC micropayments on Base",
  "type": "module",
  "main": "dist/index.js",
  "bin": {
    "x402-mcp-server": "dist/index.js"
  },
  "files": ["dist", "README.md", "LICENSE"],
  "engines": {
    "node": ">=18"
  },
  "scripts": {
    "build": "tsc",
    "postbuild": "node -e \"const fs=require('fs'),f='dist/index.js',c=fs.readFileSync(f,'utf8');if(!c.startsWith('#!/'))fs.writeFileSync(f,'#!/usr/bin/env node\\n'+c)\"",
    "prepublishOnly": "npm run build",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.11.0",
    "viem": "^2.0.0",
    "x402-fetch": "^1.1.0",
    "zod": "^4.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "publint": "^0.3.18",
    "typescript": "^5.7.0"
  }
}
```

### Zod Validation — VAL-01 coin parameter
```typescript
// Applied to x402_sentiment and x402_intelligence tools
// Source: Verified empirically against zod 4.3.6
coin: z
  .string()
  .regex(/^[A-Z0-9]{1,10}$/i)
  .describe("Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"),
```

### Zod Validation — VAL-02 url parameters
```typescript
// Applied to x402_screenshot (url param) and x402_pdf_extract (pdf_url param)
// Source: Verified empirically against zod 4.3.6
url: z
  .string()
  .url()
  .describe("URL to capture (full URL including https://)"),

pdf_url: z
  .string()
  .url()
  .describe("URL of the PDF to extract text from"),
```

### npm pack --dry-run verification
```bash
# Run after adding files whitelist to verify correct files
npm pack --dry-run
# Expected output should ONLY show:
# dist/index.js
# dist/index.d.ts
# README.md
# LICENSE
# package.json
```

### publint run
```bash
# Run after npm run build
npx publint
# Or: ./node_modules/.bin/publint
# Can also lint a tarball: publint ./x402-mcp-server-1.0.0.tgz
```

### .gitignore for public Node.js/TypeScript repo
```
# Dependencies
node_modules/

# Build output
dist/

# Environment / secrets — CRITICAL
.env
.env.*
!.env.example

# npm tarballs
*.tgz

# OS artifacts
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
```

### LICENSE file (MIT)
```
MIT License

Copyright (c) 2026 James Wisdom

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.npmignore` as blocklist | `files` whitelist as allowlist | npm has supported both for years; `files` became best practice ~2018 | Allowlist is safer — new dirs excluded by default |
| `prepublish` (ran on npm install too) | `prepublishOnly` | npm 4+ | `prepublishOnly` only runs on publish, not install |
| zod v3 validation API | zod v4 (same API, same .url()/.regex() methods) | zod v4 released 2025 | No change needed — API is backward compatible for these methods |

**Deprecated/outdated:**
- `.npmignore`: Still works but blocklist approach is error-prone for security-sensitive packages
- `prepublish` script: Replaced by `prepublishOnly` for publish-only safety hooks

## Open Questions

1. **postbuild shebang script: inline vs separate file**
   - What we know: Both approaches work. Inline keeps changes to package.json only. Separate file (e.g., `scripts/add-shebang.js`) is easier to read and debug.
   - What's unclear: Whether the inline one-liner causes issues in cross-platform environments (Windows uses `cmd` not `sh` for npm scripts).
   - Recommendation: Use inline for simplicity since target environment is Node.js on Linux/Mac (npx users). If Windows compat becomes a concern, extract to `scripts/add-shebang.cjs`.

2. **zod version pinning: ^3.0.0 or ^4.0.0**
   - What we know: MCP SDK 1.26.0 ships with zod 4.3.6. The installed version is zod 4.3.6. The code uses `import { z } from "zod"` which resolves to whatever is in node_modules.
   - What's unclear: Whether zod v4 introduced any breaking changes to `.url()` or `.regex()` for this usage. Empirical testing confirms both work.
   - Recommendation: Declare `"zod": "^4.0.0"` to match the already-installed transitive version and avoid dual-installation.

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` (config only has `"workflow": {"research": true}`). Nyquist validation is not enabled — skipping this section.

## Sources

### Primary (HIGH confidence)
- Empirical: `npm pack --dry-run` on the actual project — confirmed dangerous file exposure
- Empirical: `node --input-type=module` test of zod 4.3.6 — confirmed `.url()` and `.regex()` API works
- Empirical: `tsc && head -2 dist/index.js` — confirmed tsc 5.9.3 preserves shebang from source
- npm CLI docs — prepublishOnly lifecycle behavior
- publint v0.3.18 official site (publint.dev) — rules including BIN_FILE_NOT_EXECUTABLE

### Secondary (MEDIUM confidence)
- WebSearch: npm pack does not trigger prepublishOnly (confirmed by GitHub issue #15363 and multiple sources)
- WebSearch: publint 0.3.18 is current version (published 4 days ago per npm registry)
- choosealicense.com — MIT license text

### Tertiary (LOW confidence)
- WebSearch: TypeScript shebang preservation history — GitHub issues suggest it was fixed, but version-specific behavior not authoritatively documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — empirically verified, tools are well-established
- Architecture: HIGH — based on direct project inspection + official npm docs
- Pitfalls: HIGH — most identified from direct `npm pack --dry-run` output, not speculation

**Research date:** 2026-03-09
**Valid until:** 2026-09-09 (stable npm/zod tooling; publint version may advance but API stable)
