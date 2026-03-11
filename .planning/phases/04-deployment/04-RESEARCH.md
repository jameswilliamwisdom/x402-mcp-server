# Phase 4: Deployment - Research

**Researched:** 2026-03-11
**Domain:** macOS server deployment — Homebrew nginx, rsync, launchctl
**Confidence:** HIGH (server directly inspected via SSH; nginx docs verified)

## Summary

Phase 4 deploys the pre-built Astro static site (`site/dist/`) to a home macOS server
at `10.0.0.2` via rsync, configures nginx to serve it on port 80, and verifies with
automated smoke tests. All decisions are locked in CONTEXT.md. The critical
infrastructure discovery is that **Homebrew is not installed on the server** — the
`~/.zprofile` references `/opt/homebrew/bin/brew` but that binary does not exist. The
server is x86_64 macOS 12 (Monterey), and Homebrew's nginx formula has no pre-built
bottle for Monterey/x86_64. Homebrew must be installed first (build-from-source for
nginx is expected on this OS version, taking 5–15 minutes), OR nginx can be compiled
directly from source without Homebrew.

A second critical finding: **port 8080 is already in use** on the server by a Python
process. The default Homebrew nginx config listens on 8080 (to avoid requiring sudo).
Nginx must be configured for port 80 instead, which requires running as root. This
means using `/Library/LaunchDaemons/` (not `~/Library/LaunchAgents/`) for auto-start,
or running nginx directly with `sudo nginx`.

The Astro site is already built (`site/dist/` has valid static output). The rsync
command is straightforward. The main work is server-side: installing Homebrew, getting
nginx running, creating `/var/www/x402-network/`, and configuring nginx correctly for
the IP-only, HTTP-only, static site case.

**Primary recommendation:** Install Homebrew via the official script on the server
first. Then `brew install nginx` (expects source build on Monterey — allow 10+ min).
Configure nginx for port 80 via `/Library/LaunchDaemons/` plist. Use `SITE_URL`
env var set to `http://10.0.0.2` when rebuilding for proper OG image URLs before deploy.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Server & Access**
- Home server running macOS at `10.0.0.2`
- SSH access: `ssh jameswisdom@10.0.0.2` (key-based auth already configured)
- Target directory: `/var/www/x402-network/`
- nginx — may or may not be installed already (check during execution, install via Homebrew if missing)
- Port forwarding status unknown — not needed for local-only access

**Domain & DNS**
- No domain for v1 — serve on IP address only (`http://10.0.0.2`)
- HTTP only — no TLS (Let's Encrypt requires a domain)
- Start local network only, go public later
- Public IP type (static vs dynamic) unknown — not relevant until going public

**TLS & Security**
- HTTP-only for now — TLS deferred until domain is purchased
- Future plan: Cloudflare proxy for TLS + CDN + IP hiding
- nginx must deny all dotfile paths (`/.planning/`, `/.git/`, `/.env`, etc.) — defense in depth
- Standard security headers: X-Frame-Options, X-Content-Type-Options, Referrer-Policy

**Deploy Workflow**
- `site/deploy.sh` — builds (`npm run build`) + rsyncs `dist/` to server
- Separate one-time `site/setup-server.sh` for nginx install + config on the server
- Automated smoke tests in deploy.sh — curl key pages, check status codes, verify OG tags
- No CI/CD — manual deploys via script

### Claude's Discretion
- OG image site URL handling (currently `https://x402.todo` placeholder) — Claude decides whether to update to local IP or leave as placeholder
- nginx config details (worker_processes, gzip, cache headers)
- Exact smoke test assertions
- Whether setup-server.sh runs locally or is copied to server and run there

### Deferred Ideas (OUT OF SCOPE)
- Domain purchase and DNS setup — separate effort when ready to go public
- TLS via Cloudflare proxy — requires domain first
- Port forwarding for public internet access — after local deployment is verified
- CI/CD pipeline — overkill for a single-person project at v1
- DDNS for dynamic IP — only needed if going public without a static IP
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEPLOY-02 | Site deployed to home server (no domain, IP/subdomain for now) | rsync pattern, nginx config, Homebrew install, launchctl plist, smoke tests all documented below |
</phase_requirements>

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| rsync | 2.6.9 (server), openrsync 2.6.9-compat (local) | Transfer `site/dist/` to server | Pre-installed macOS, SSH-native, atomic `--delete` |
| nginx | 1.29.6 (latest Homebrew formula) | Serve static files on port 80 | Industry standard; handles dotfile deny, headers, gzip trivially |
| Homebrew | Latest (install via official script) | Package manager for nginx | Standard macOS package manager; nginx formula well maintained |
| launchctl | macOS built-in | Auto-start nginx on boot | macOS native; LaunchDaemon runs as root (required for port 80) |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `brew services` | Service lifecycle shortcut | NOT reliable for port 80 (runs as user, not root) — use direct launchctl plist instead |
| curl | Smoke testing | In deploy.sh to verify HTTP 200, OG tags |
| `nginx -t` | Config validation | Before reloading nginx |
| `nginx -s reload` | Zero-downtime config reload | After updating nginx config |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Homebrew nginx | Source-compiled nginx | Source compile gives full control, avoids Homebrew complexity on Monterey; but Homebrew is cleaner for ongoing updates |
| `/Library/LaunchDaemons/` plist | `sudo nginx` at terminal | plist survives reboots; terminal command is ephemeral |
| `brew services start nginx` | Direct launchctl load | `brew services` runs as user (can't bind port 80); plist in LaunchDaemons runs as root |

**Installation (server-side, run in `setup-server.sh` or manually):**
```bash
# Step 1: Install Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Step 2: Install nginx (will build from source on Monterey — 5–15 min)
/usr/local/bin/brew install nginx

# Step 3: Create web root
sudo mkdir -p /var/www/x402-network
sudo chown jameswisdom:staff /var/www/x402-network
```

---

## Architecture Patterns

### Recommended File Structure

```
site/
├── deploy.sh              # local: build + rsync + smoke test
├── setup-server.sh        # local: SSH to server, install Homebrew + nginx, configure
└── dist/                  # Astro build output (already exists)

[server] /usr/local/etc/nginx/
├── nginx.conf             # Homebrew default — keep minimal, add include
└── servers/
    └── x402-network.conf  # Site-specific config

[server] /var/www/x402-network/   # Web root (rsync target)
[server] /Library/LaunchDaemons/homebrew.mxcl.nginx.plist  # Boot-time autostart
```

### Pattern 1: Homebrew nginx on macOS Intel x86_64

**What:** Homebrew installs to `/usr/local` on Intel Macs. Nginx config root is
`/usr/local/etc/nginx/`. The nginx binary is at `/usr/local/opt/nginx/bin/nginx`
(symlinked from `/usr/local/bin/nginx`). The default Homebrew nginx.conf includes all
files in `/usr/local/etc/nginx/servers/`.

**Server reality check:** The server is x86_64 macOS 12.7.6 (Monterey). Homebrew has
no pre-built bottle for nginx on Monterey — it will compile from source. This takes
5–15 minutes but works. The Xcode Command Line Tools (version 14.2) are already
installed on the server, which is required.

**Important:** The server's `~/.zprofile` sets Homebrew at `/opt/homebrew` (ARM path),
which doesn't exist. After installing Homebrew on this Intel machine, the prefix will
be `/usr/local`. The `~/.zprofile` will need updating, OR `setup-server.sh` should
call Homebrew by absolute path (`/usr/local/bin/brew`).

```bash
# Verify Homebrew prefix after install on Intel Mac
/usr/local/bin/brew --prefix
# → /usr/local

# nginx config location
ls /usr/local/etc/nginx/
# → nginx.conf  servers/

# nginx binary
ls -la /usr/local/opt/nginx/bin/nginx
```

### Pattern 2: nginx Config for HTTP-Only Static Site

**nginx server block for IP-only, HTTP-only, static site with SPA fallback:**

```nginx
# /usr/local/etc/nginx/servers/x402-network.conf
server {
    listen 80;
    server_name _;                        # match any hostname/IP

    root /var/www/x402-network;
    index index.html;

    # Static SPA fallback — Astro's router handles client-side nav
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Deny all dotfile paths — defense in depth
    location ~ /\. {
        deny all;
        return 404;
    }

    # Security headers (HTTP-only — no HSTS since not TLS)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip for text assets
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/javascript application/javascript
               application/json image/svg+xml;
    gzip_comp_level 6;
    gzip_min_length 256;

    # Long-term cache for fingerprinted Astro assets
    location /_astro/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # No-cache for HTML (always fresh)
    location ~* \.html$ {
        add_header Cache-Control "no-cache";
    }
}
```

**Note:** The default Homebrew nginx.conf listens on 8080. The site config above
overrides this by using port 80 explicitly. The main `nginx.conf` must include the
servers directory:
```nginx
# In /usr/local/etc/nginx/nginx.conf — already there by default:
include servers/*;
```

### Pattern 3: Port 80 via LaunchDaemon (auto-start on boot)

Port 80 requires root. `brew services start nginx` runs nginx as the current user
and cannot bind port 80. The correct approach is a LaunchDaemon plist in
`/Library/LaunchDaemons/`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>homebrew.mxcl.nginx</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>ProgramArguments</key>
    <array>
      <string>/usr/local/opt/nginx/bin/nginx</string>
      <string>-g</string>
      <string>daemon off;</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/usr/local</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/nginx/error.log</string>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/nginx/access.log</string>
  </dict>
</plist>
```

```bash
# Install and start:
sudo cp homebrew.mxcl.nginx.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/homebrew.mxcl.nginx.plist
sudo launchctl load -w /Library/LaunchDaemons/homebrew.mxcl.nginx.plist

# Reload after config change:
sudo nginx -s reload

# Stop:
sudo launchctl unload -w /Library/LaunchDaemons/homebrew.mxcl.nginx.plist
sudo nginx -s stop
```

**Critical:** Do NOT include a `UserName` key in the plist — omitting it causes the
daemon to run as root, which is required for port 80.

### Pattern 4: rsync Deploy Command

```bash
# From local dev machine:
rsync -av --delete \
  site/dist/ \
  jameswisdom@10.0.0.2:/var/www/x402-network/
```

**Trailing slash on source is critical.** `site/dist/` (with slash) copies the
*contents* of dist into the target. Without the slash, rsync would copy the `dist`
directory itself, creating `/var/www/x402-network/dist/`.

**Both machines run rsync 2.6.9-compatible (protocol 29).** The `--delete` flag is
supported on both. No compatibility issues.

### Pattern 5: Smoke Test Script (in deploy.sh)

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="http://10.0.0.2"

smoke_check() {
    local url="$1"
    local expected_status="${2:-200}"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")
    if [[ "$status" != "$expected_status" ]]; then
        echo "FAIL: $url returned $status (expected $expected_status)"
        exit 1
    fi
    echo "PASS: $url → $status"
}

# Status code checks
smoke_check "$BASE/"          200
smoke_check "$BASE/pricing"   200
smoke_check "$BASE/getting-started" 200
smoke_check "$BASE/api-reference"   200
smoke_check "$BASE/wallet-setup"    200
smoke_check "$BASE/.planning/"      404
smoke_check "$BASE/.git/"           404

# OG meta tag present in homepage
og_check=$(curl -s --max-time 10 "$BASE/" | grep -c 'og:image')
if [[ "$og_check" -eq 0 ]]; then
    echo "FAIL: OG meta tag missing from homepage"
    exit 1
fi
echo "PASS: OG meta tag present"

echo ""
echo "All smoke tests passed."
```

### Anti-Patterns to Avoid

- **Using `brew services start nginx` for port 80**: Runs as user, cannot bind port 80.
  Use LaunchDaemon plist instead.
- **Omitting trailing slash on rsync source**: `site/dist` (no slash) nests `dist/` inside
  the target directory instead of syncing contents.
- **Using default nginx port 8080**: Port 8080 is already occupied by a Python process
  on the server. Configure nginx explicitly for port 80.
- **Not running `nginx -t` before reload**: Always validate config before applying.
- **SSH interactive session for setup**: The `setup-server.sh` should use
  `ssh jameswisdom@10.0.0.2 "zsh -c '...'"` or heredoc, not interactive.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dotfile path blocking | Custom path filter | `location ~ /\. { deny all; }` in nginx | nginx built-in, handles all dotfile patterns |
| gzip compression | Custom middleware | `gzip on;` in nginx | nginx handles negotiation, vary headers, level |
| Cache headers | Custom response logic | `expires` + `Cache-Control` in nginx location blocks | Correct immutable/no-cache split for SPAs is non-trivial |
| Static file serving | Node.js `serve` or Python http.server | nginx | Purpose-built, survives reboots, correct MIME types |

**Key insight:** nginx handles all static site concerns (MIME types, compression,
caching, security headers, path blocking) with 20 lines of config. Don't introduce
a Node/Python server for a purely static site.

---

## Common Pitfalls

### Pitfall 1: Homebrew Not in PATH during SSH non-login shell

**What goes wrong:** `ssh jameswisdom@10.0.0.2 "brew install nginx"` fails with
`brew: command not found`. Homebrew is initialized in `~/.zprofile` (login shells only).
Non-interactive SSH sessions don't source `.zprofile`.

**Why it happens:** macOS SSH default shell is bash or zsh without login flag, so
`~/.zprofile` is not sourced.

**How to avoid:** Use `ssh ... "zsh -l -c 'brew install nginx'"` (login shell) OR
reference Homebrew by absolute path: `/usr/local/bin/brew install nginx` (after
Homebrew is installed to `/usr/local` on Intel).

**Warning signs:** `command not found: brew` in SSH output.

### Pitfall 2: Port 8080 Already In Use

**What goes wrong:** nginx starts but is unreachable on port 80. OR nginx fails to
start because port 8080 is in use (default Homebrew config).

**Why it happens:** Homebrew's default `nginx.conf` sets `listen 8080`. Port 8080 is
already bound by a Python process (`lsof -i :8080` confirmed). The site config must
explicitly use `listen 80`.

**How to avoid:** The custom site config in `servers/x402-network.conf` listens on
port 80. Optionally remove the default `listen 8080` from the main `nginx.conf` to
avoid confusion.

**Warning signs:** curl to `http://10.0.0.2` returns connection refused; `lsof -i :80`
shows nothing.

### Pitfall 3: Homebrew Build-from-Source on Monterey

**What goes wrong:** `brew install nginx` appears to hang or takes 15+ minutes on the
server. User aborts thinking it failed.

**Why it happens:** Homebrew has no pre-built bottle for nginx on macOS 12 (Monterey).
It must compile nginx (and its dependencies openssl@3, pcre2) from source. This is
expected and normal.

**How to avoid:** `setup-server.sh` should print a warning: "nginx will build from
source on this macOS version — allow 15+ minutes." Do not abort the process.

**Warning signs:** `brew install` output shows "Building from source..." with compiler
lines streaming.

### Pitfall 4: rsync Trailing Slash

**What goes wrong:** `/var/www/x402-network/` ends up with a nested `dist/` directory
inside it: `/var/www/x402-network/dist/index.html` instead of
`/var/www/x402-network/index.html`.

**Why it happens:** `rsync -av --delete site/dist jameswisdom@10.0.0.2:/var/www/x402-network/`
(no trailing slash on source) copies the `dist` directory itself, not its contents.

**How to avoid:** Always `site/dist/` (with trailing slash). Verify with `ls` on server
after first rsync.

**Warning signs:** nginx 404 on all URLs; `/var/www/x402-network/` listing shows only
a `dist/` subdirectory.

### Pitfall 5: /var/www Does Not Exist

**What goes wrong:** rsync fails with "No such file or directory" for
`/var/www/x402-network/`.

**Why it happens:** `/var/www` does not exist on the server (confirmed). macOS does not
create this directory by default.

**How to avoid:** `setup-server.sh` must `sudo mkdir -p /var/www/x402-network` and
`sudo chown jameswisdom:staff /var/www/x402-network`. The chown ensures rsync (running
as `jameswisdom` over SSH) can write to the directory without sudo.

**Warning signs:** rsync exits with error about missing directory.

### Pitfall 6: OG Image URL Placeholder in Built Output

**What goes wrong:** The deployed site has `og:image` pointing to
`https://x402.todo/og-image.png` (the placeholder). This is fine for local-only
deployment (OG crawlers can't reach a local IP anyway) but may cause confusion.

**Why it happens:** `astro.config.mjs` uses `process.env.SITE_URL || 'https://x402.todo'`.
When `deploy.sh` runs `npm run build` without setting `SITE_URL`, the placeholder is used.

**How to avoid (Claude's discretion):** Set `SITE_URL=http://10.0.0.2` before building
in `deploy.sh`. This makes OG URLs technically correct for the local IP but they still
won't be crawlable. Recommended: set it to `http://10.0.0.2` for correctness — the
smoke test checks for OG tag presence, not the URL value.

**Warning signs:** `og:image` content is `https://x402.todo/...` in curl output.

### Pitfall 7: setup-server.sh Requires Interactive sudo Password

**What goes wrong:** `setup-server.sh` hangs waiting for a sudo password when run
non-interactively.

**Why it happens:** Commands like `sudo mkdir -p /var/www/x402-network` prompt for
a password in SSH.

**How to avoid:** `setup-server.sh` should be designed to run as an interactive SSH
session (user runs it locally, which SSHs and prompts them for sudo password at the
correct point) OR document that the user must run it from an active SSH session to the
server. The `-t` SSH flag allocates a pseudo-TTY for password prompts:
`ssh -t jameswisdom@10.0.0.2 "sudo mkdir -p /var/www/x402-network"`.

---

## Code Examples

### deploy.sh (complete pattern)

```bash
#!/usr/bin/env bash
# site/deploy.sh — build, rsync, smoke test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="jameswisdom@10.0.0.2"
REMOTE_DIR="/var/www/x402-network/"
BASE_URL="http://10.0.0.2"

echo "==> Building site..."
cd "$SCRIPT_DIR"
SITE_URL="$BASE_URL" npm run build

echo "==> Deploying to server..."
rsync -av --delete "$SCRIPT_DIR/dist/" "$SERVER:$REMOTE_DIR"

echo "==> Running smoke tests..."

smoke_check() {
    local url="$1"
    local expected="${2:-200}"
    local got
    got=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")
    if [[ "$got" != "$expected" ]]; then
        echo "FAIL: $url → $got (expected $expected)"
        exit 1
    fi
    echo "PASS: $url → $got"
}

smoke_check "$BASE_URL/"                 200
smoke_check "$BASE_URL/pricing"          200
smoke_check "$BASE_URL/getting-started"  200
smoke_check "$BASE_URL/api-reference"    200
smoke_check "$BASE_URL/wallet-setup"     200
smoke_check "$BASE_URL/.planning/"       404
smoke_check "$BASE_URL/.git/"            404

# OG meta tag verification
if ! curl -s --max-time 10 "$BASE_URL/" | grep -q 'og:image'; then
    echo "FAIL: og:image meta tag missing from homepage"
    exit 1
fi
echo "PASS: og:image meta tag present"

echo ""
echo "Deployment complete. Site live at $BASE_URL"
```

### setup-server.sh (pattern — runs locally, SSHes to server)

```bash
#!/usr/bin/env bash
# site/setup-server.sh — one-time server setup
# Run from local dev machine. Some commands require sudo on the server
# (will prompt for password when SSH allocates a TTY).
set -euo pipefail

SERVER="jameswisdom@10.0.0.2"
BREW="/usr/local/bin/brew"  # Intel Mac Homebrew prefix

echo "==> Checking Homebrew..."
if ! ssh "$SERVER" "test -f $BREW"; then
    echo "Installing Homebrew (this may take a while on macOS Monterey)..."
    ssh "$SERVER" '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
fi

echo "==> Installing nginx (may build from source — allow 15+ minutes)..."
ssh "$SERVER" "$BREW install nginx"

echo "==> Creating web root..."
ssh -t "$SERVER" "sudo mkdir -p /var/www/x402-network && sudo chown jameswisdom:staff /var/www/x402-network"

echo "==> Writing nginx site config..."
ssh "$SERVER" "cat > /tmp/x402-network.conf" << 'NGINXCONF'
server {
    listen 80;
    server_name _;

    root /var/www/x402-network;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~ /\. {
        deny all;
        return 404;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/javascript application/javascript
               application/json image/svg+xml;
    gzip_comp_level 6;
    gzip_min_length 256;

    location /_astro/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location ~* \.html$ {
        add_header Cache-Control "no-cache";
    }
}
NGINXCONF

ssh "$SERVER" "sudo mv /tmp/x402-network.conf /usr/local/etc/nginx/servers/x402-network.conf"

echo "==> Installing LaunchDaemon plist for auto-start..."
# (write plist to /tmp, then move to LaunchDaemons with sudo)

echo "==> Validating nginx config..."
ssh "$SERVER" "sudo /usr/local/opt/nginx/bin/nginx -t"

echo "==> Starting nginx..."
ssh -t "$SERVER" "sudo launchctl load -w /Library/LaunchDaemons/homebrew.mxcl.nginx.plist"

echo "Server setup complete."
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `brew services start nginx` for port 80 | LaunchDaemon plist in `/Library/LaunchDaemons/` | Always the case | brew services runs as user; LaunchDaemon runs as root |
| `openssl` from system for nginx | `openssl@3` as Homebrew dependency | nginx formula | Homebrew manages OpenSSL separately from macOS system |
| Homebrew at `/usr/local` on Apple Silicon | `/opt/homebrew` on ARM, `/usr/local` on Intel | 2020 (Apple Silicon) | Server is Intel → `/usr/local`; M1+ → `/opt/homebrew` |
| Hardcoded nginx version in plist path | `/usr/local/opt/nginx/bin/nginx` (opt symlink, version-agnostic) | Homebrew convention | Opt symlink survives `brew upgrade nginx` without plist edit |

**Deprecated/outdated:**
- `brew services start nginx` for port 80: Creates a LaunchAgent (user-level), cannot bind port 80.
- `/usr/local/Cellar/nginx/<version>/bin/nginx` in plist: Version-specific path breaks after upgrades; use `/usr/local/opt/nginx/bin/nginx` instead.

---

## Open Questions

1. **Does `setup-server.sh` need to handle the Homebrew `~/.zprofile` ARM path leftover?**
   - What we know: Server `~/.zprofile` has `eval "$(/opt/homebrew/bin/brew shellenv)"` which fails (no binary at that path)
   - What's unclear: Will the failed eval silently continue or break zsh login?
   - Recommendation: `setup-server.sh` should add the correct Intel Homebrew eval line to `~/.zprofile` after install, or rely on absolute paths throughout.

2. **Does `/var/www` require root to create on macOS Monterey?**
   - What we know: `/var/www` doesn't exist; `/var/` is owned by root
   - What's unclear: Whether `/var/` is on a system-protected volume under SIP
   - Recommendation: Use `sudo mkdir -p /var/www/x402-network` and then `chown` to user. Test this explicitly in setup-server.sh before assuming it works.

3. **SIP (System Integrity Protection) and /var/www**
   - What we know: macOS SIP protects `/System`, `/usr` (with exceptions for `/usr/local`), not `/var`
   - What's unclear: macOS Monterey-specific `/var` symlink behavior (some versions symlink `/var` to `/private/var`)
   - Recommendation: Create as `sudo mkdir -p /private/var/www/x402-network` if `/var/www` fails — `/var` is a symlink to `/private/var` on macOS.

---

## Sources

### Primary (HIGH confidence)
- SSH live inspection of server (`10.0.0.2`) — OS version, architecture, existing services, port usage, Homebrew presence, rsync version
- `formulae.brew.sh/formula/nginx` — nginx 1.29.6, no Monterey bottle confirmed
- `docs.brew.sh/Installation` — Intel prefix `/usr/local`, install command, requirements

### Secondary (MEDIUM confidence)
- `summercode.com/wiki/running-homebrewed-nginx-with-sudo-on-mac-os-x/` — LaunchDaemon plist pattern for port 80, verified against launchd documentation
- Homebrew Discussions #5603 — macOS 12 not supported for bottles, must build from source
- `jdeen.com/blog/installation-of-nginx-in-macos-homebrew` — config paths `/usr/local/etc/nginx/`, `servers/` include directory
- nginx documentation (docs.nginx.com) — `try_files`, security headers, gzip config

### Tertiary (LOW confidence)
- Build time estimate "5–15 minutes for source compile" — based on typical compile times; actual time depends on server CPU

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — server directly inspected, all tool versions confirmed
- Architecture: HIGH — nginx config patterns from official docs + verified working patterns
- Pitfalls: HIGH — port conflicts confirmed via lsof, rsync slash behavior is documented, Homebrew bottle gap confirmed via formulae.brew.sh
- Homebrew install time: LOW — estimate only; no benchmark available

**Research date:** 2026-03-11
**Valid until:** 2026-06-11 (stable infrastructure; nginx/Homebrew versions may update but patterns remain constant)
