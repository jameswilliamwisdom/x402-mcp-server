---
phase: 01-package-hardening-input-validation
plan: 01
subsystem: infra
tags: [npm, package.json, publishing, license, gitignore, zod, publint]

# Dependency graph
requires: []
provides:
  - "npm files whitelist preventing .env/src/.planning exposure on publish"
  - "MIT LICENSE at repo root"
  - "Comprehensive .gitignore for public Node.js/TypeScript repo"
  - "zod as direct dependency in package.json"
  - "publint devDependency for package validation"
  - "postbuild shebang injection guard"
  - "prepublishOnly lifecycle hook running clean build before every publish"
affects:
  - "02-npm-publish"
  - "all plans that run npm run build"

# Tech tracking
tech-stack:
  added:
    - "zod ^4.3.6 (promoted from transitive to direct dependency)"
    - "publint ^0.3.18 (devDependency, package publishing validator)"
  patterns:
    - "files whitelist pattern: explicit allowlist in package.json rather than relying on .npmignore"
    - "postbuild shebang guard: defensive injection after tsc compilation"

key-files:
  created:
    - "LICENSE"
  modified:
    - "package.json"
    - "package-lock.json"
    - ".gitignore"

key-decisions:
  - "files whitelist uses allowlist approach (files field) not denylist (.npmignore) — simpler and safer"
  - "postbuild shebang guard is defensive: tsc 5.9.3 preserves shebangs, but guard ensures correctness regardless of future tsc behavior"
  - ".planning/ intentionally NOT in .gitignore — planning docs are committed to repo per project decision"
  - "zod version resolved to ^4.3.6 (latest ^4 series) — compatible with ^4.0.0 requirement"

patterns-established:
  - "Atomic task commits: each task gets its own commit with chore(01-01): prefix"
  - "files whitelist is the canonical publishing safety mechanism for this project"

requirements-completed:
  - PKG-01
  - PKG-02
  - PKG-03
  - PKG-04
  - PKG-05
  - PKG-06

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 1 Plan 01: Package Hardening — files whitelist, lifecycle scripts, MIT LICENSE, .gitignore Summary

**npm package.json hardened with files allowlist (["dist","README.md","LICENSE"]), postbuild shebang guard, prepublishOnly hook, zod direct dep, publint devDep, MIT LICENSE, and expanded .gitignore for public repo**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T22:20:26Z
- **Completed:** 2026-03-09T22:22:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `files` whitelist to package.json — highest-risk item resolved: npm publish can no longer expose `.env`, `src/`, or `.planning/`
- Added `engines`, `postbuild`, and `prepublishOnly` scripts — build pipeline is now safe and reproducible
- Promoted `zod` to direct dependency and installed `publint` as devDependency
- Created MIT LICENSE with correct copyright year and name
- Replaced 3-line .gitignore with comprehensive public-repo patterns (secrets, tarballs, OS artifacts, IDE dirs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden package.json — files whitelist, scripts, engines, dependencies** - `931ee93` (chore)
2. **Task 2: Create LICENSE and update .gitignore for public repo** - `3441f2d` (chore)

**Plan metadata:** (included in docs commit below)

## Files Created/Modified

- `/Users/jameswisdom/projects/x402-mcp-server/package.json` - Added files whitelist, engines, postbuild, prepublishOnly, zod dep, publint devDep
- `/Users/jameswisdom/projects/x402-mcp-server/package-lock.json` - Updated with zod ^4.3.6 and publint ^0.3.18
- `/Users/jameswisdom/projects/x402-mcp-server/LICENSE` - MIT license, Copyright (c) 2026 James Wisdom
- `/Users/jameswisdom/projects/x402-mcp-server/.gitignore` - Expanded from 3 lines to 20 lines with full public-repo patterns

## Decisions Made

- Used `files` allowlist (not `.npmignore`) — simpler and more explicit: only `dist/`, `README.md`, `LICENSE` in tarball
- `postbuild` is defensive: tsc 5.9.3 already preserves shebangs, but the guard ensures correctness regardless of future compiler behavior
- `.planning/` is NOT gitignored — committed to repo per project decision (project history belongs in git)
- `zod` resolved to `^4.3.6` (latest stable ^4 series) — fully satisfies the `^4.0.0` requirement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both tasks completed without issues. The npm install commands ran cleanly. Verification script confirmed all 8 package.json checks pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Package hardening complete. All PKG-01 through PKG-06 requirements satisfied.
- Ready for Plan 02: Input validation (Zod schema tightening on coin/url/pdf_url params + full build & package verification)
- No blockers.

---
*Phase: 01-package-hardening-input-validation*
*Completed: 2026-03-09*
