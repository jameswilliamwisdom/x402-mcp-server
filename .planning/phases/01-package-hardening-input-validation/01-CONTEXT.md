# Phase 1: Package Hardening + Input Validation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock down the npm package boundary and tighten input validation so the package is safe to publish publicly. No new runtime features — this is purely security hardening and configuration. The `files` whitelist is the highest-risk item: a publish without it could expose `X402_PRIVATE_KEY` to the public registry.

</domain>

<decisions>
## Implementation Decisions

### Package Contents
- npm tarball ships ONLY: `dist/index.js`, `dist/index.d.ts`, `README.md`, `LICENSE`, `package.json`
- Exclude: `openapi/`, `src/`, `.planning/`, `site/`, `tsconfig.json`, `*.tgz`
- `files` field in package.json: `["dist", "README.md", "LICENSE"]`
- Unscoped package name: `x402-mcp-server`

### Input Validation
- Coin regex: `/^[A-Z0-9]{1,10}$/i` — alphanumeric only, 1-10 chars. Blocks path traversal. No hyphens, dots, or special chars.
- URL validation: `z.string().url()` — well-formed URLs only, any scheme. Backend handles scheme restrictions.
- Error messages: Zod defaults — no custom error messages needed for v1.

### Repo Hygiene
- Create .gitignore (Claude's discretion on exact contents — standard Node patterns + project-specific exclusions)
- `.planning/` docs committed to git (project history, useful for future context)
- Repo will be pushed to GitHub as a public repo (matches MIT license)

### Shebang Handling
- Postbuild npm script that checks `dist/index.js` and prepends `#!/usr/bin/env node` if tsc stripped it
- Runs automatically after every `npm run build`

### Pre-Publish Testing
- `npm pack` to create tarball → install in temp dir → verify `npx` works and MCP server starts
- `publint` validation for package export correctness
- Manual verification only — no test framework for v1

### npm Account
- Not currently logged in (`npm whoami` returns ENEEDAUTH)
- `npm adduser` is a Phase 2 prerequisite, not Phase 1

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The research identified the exact tools and patterns to use (publint, postbuild shebang injection, files whitelist).

</specifics>

<deferred>
## Deferred Ideas

- Automated unit tests for Zod validation schemas — could add in a future milestone if regressions become a concern
- CI/CD pipeline for automated npm publish — explicitly out of scope for v1.0

</deferred>

---

*Phase: 01-package-hardening-input-validation*
*Context gathered: 2026-03-09*
