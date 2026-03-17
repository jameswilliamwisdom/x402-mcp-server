#!/usr/bin/env bash
# site/deploy.sh — build, rsync, smoke test
# Run from the project root (x402-mcp-server/) or from within site/.
# Usage: bash site/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="jameswisdom@10.0.0.2"
REMOTE_DIR="/var/www/x402-network/"
BASE_URL="https://usebismuth.com"

# ── Build ────────────────────────────────────────────────────────────────────
echo "==> Building site (SITE_URL=$BASE_URL)..."
cd "$SCRIPT_DIR"
SITE_URL="$BASE_URL" npm run build

# Verify build output before deploying
if [[ ! -f "$SCRIPT_DIR/dist/index.html" ]]; then
    echo "FAIL: dist/index.html not found after build"
    exit 1
fi
if [[ -d "$SCRIPT_DIR/dist/server" ]]; then
    echo "FAIL: dist/server/ directory found — SSR output detected (expected static)"
    exit 1
fi
echo "PASS: static build verified (index.html present, no server/ dir)"

# ── Deploy ───────────────────────────────────────────────────────────────────
echo ""
echo "==> Deploying to $SERVER:$REMOTE_DIR..."
# Trailing slash on source is CRITICAL — syncs contents, not the dist/ dir itself
rsync -av --delete "$SCRIPT_DIR/dist/" "$SERVER:$REMOTE_DIR"
echo "PASS: rsync complete"

# ── Smoke Tests ──────────────────────────────────────────────────────────────
echo ""
echo "==> Running smoke tests against $BASE_URL..."

smoke_check() {
    local url="$1"
    local expected="${2:-200}"
    local got
    got=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 10 "$url")
    if [[ "$got" != "$expected" ]]; then
        echo "FAIL: $url → HTTP $got (expected $expected)"
        exit 1
    fi
    echo "PASS: $url → HTTP $got"
}

# Page availability (use trailing slashes — nginx redirects non-slash paths to slash paths)
smoke_check "$BASE_URL/"                  200
smoke_check "$BASE_URL/pricing/"          200
smoke_check "$BASE_URL/getting-started/"  200
smoke_check "$BASE_URL/api-reference/"    200
smoke_check "$BASE_URL/wallet-setup/"     200
smoke_check "$BASE_URL/apis/scraping/"           200
smoke_check "$BASE_URL/apis/file-conversion/"    200
smoke_check "$BASE_URL/apis/web-search/"         200
smoke_check "$BASE_URL/apis/email/"              200
smoke_check "$BASE_URL/apis/audio-transcription/" 200

# Security: dotfile paths must return 404
smoke_check "$BASE_URL/.planning/"       404
smoke_check "$BASE_URL/.git/"            404

# OG meta tag present (og:image must appear in homepage HTML)
OG_COUNT=$(curl -s --max-time 10 "$BASE_URL/" | grep -c 'og:image' || true)
if [[ "$OG_COUNT" -eq 0 ]]; then
    echo "FAIL: og:image meta tag missing from $BASE_URL/"
    exit 1
fi
echo "PASS: og:image meta tag present in homepage HTML"

# OG image URL must NOT be the placeholder or old local IP
OG_PLACEHOLDER=$(curl -s --max-time 10 "$BASE_URL/" | grep -cE 'x402\.todo|10\.0\.0\.2' || true)
if [[ "$OG_PLACEHOLDER" -gt 0 ]]; then
    echo "FAIL: placeholder URL 'x402.todo' or old IP '10.0.0.2' found in homepage — SITE_URL was not set during build"
    exit 1
fi
echo "PASS: og:image URL is not a placeholder or old local IP"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "All smoke tests passed."
echo "Bismuth brand site is live at $BASE_URL"
