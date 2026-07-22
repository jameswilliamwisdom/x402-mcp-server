# npm supply-chain hardening for `x402-mcp-server`

The `x402-mcp-server` package is distributed via npm and installed by agent developers into Claude Code, Cursor, and other MCP-aware environments. A compromised release would run in every downstream user's terminal or IDE with their filesystem + credential access. The blast radius is unusually high for a small package.

This doc lists the four hardening steps James should run once on his npm account. All require his authentication; none can be automated.

## 1. Enable 2FA on the npm account

Log in at https://www.npmjs.com and go to `Profile → Account → Two-Factor Authentication`. Choose "Authorization and publishing" (the strictest mode — 2FA required for login AND every publish). Add a TOTP authenticator (Aegis on Android, 1Password on desktop, etc.). Save the recovery codes to `~/.bugs/secrets/npm-recovery-codes.txt` with 0600 permissions.

Verify by attempting `npm whoami` — should prompt for 2FA if you haven't authenticated recently.

## 2. Enable publish 2FA on the package itself

Even with account 2FA, the package needs its own publish gate. Run:

```bash
npm access set 2fa=publish x402-mcp-server
```

This is separate from account 2FA — some tokens can publish without account 2FA if the package doesn't require it.

Verify:
```bash
npm access get 2fa x402-mcp-server
# Should print: publish
```

## 3. Enable npm provenance signing

Provenance links each published version back to the exact GitHub Actions run that built it. Downstream users can verify the package came from the claimed source. See https://docs.npmjs.com/generating-provenance-statements

Requires switching the release path to GitHub Actions. Suggested minimum workflow at `.github/workflows/release.yml`:

```yaml
name: release
on:
  release:
    types: [published]
permissions:
  contents: read
  id-token: write  # required for provenance
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm run build
      - run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

The `NPM_TOKEN` secret is a granular access token created in the npm UI, scoped to publish only the x402-mcp-server package. Do NOT use a classic token — those are unscoped.

## 4. Rotate any existing npm tokens

If James has previously created classic npm tokens (long-lived, unscoped), revoke them. From the npm UI: `Access Tokens → revoke all classic tokens`. Any local `~/.npmrc` file with `//registry.npmjs.org/:_authToken=...` should be checked for a stale token and cleaned up.

For local dev, use `npm login` interactively when you need to publish — the session token is short-lived and 2FA-gated.

## Additional considerations

**Package name reservation.** Squat adjacent names to prevent typosquat attacks. Cheap ($0 to publish an empty package) and worth doing:
- `x402-mcp-server-typo-guard` — publish an empty stub with a README pointing at the real package
- `bismuth-mcp` — reserve for the v3 rebrand
- `@bismuth/mcp` — reserve the scoped name

**Dependency audit.** Run `npm audit --audit-level=moderate` before every release. If issues surface, evaluate; do not blindly `npm audit fix` — it can silently pull in newer major versions that break the build.

**Lockfile discipline.** `package-lock.json` is committed. Never install with `npm install --no-package-lock`. The lockfile pins transitive dependencies, which is the primary defense against transitive supply-chain drift.

**Watch for typosquats after publish.** Every few weeks, `npm search x402` — if a package appears that impersonates ours, report to npm security via https://github.com/npm/security-holding-package

## Priority

- **Do this week:** steps 1 + 2 + 4 (account 2FA + package 2FA + token cleanup). No code changes needed. ~20 minutes total.
- **Do this month:** step 3 (provenance signing via GitHub Actions). Requires setting up the workflow and the granular token.
- **Do quarterly:** review `npm audit`, check for typosquats, rotate the GHA-scoped token.

---

**Last updated:** 2026-07-22. Update after any npm account or CI change.
