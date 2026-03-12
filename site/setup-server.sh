#!/usr/bin/env bash
# site/setup-server.sh — one-time server setup for 10.0.0.2
# Run from local dev machine. Requires key-based SSH to jameswisdom@10.0.0.2.
# Some steps use `ssh -t` to allocate a TTY for interactive sudo password prompts.
set -euo pipefail

SERVER="jameswisdom@10.0.0.2"
BREW="/usr/local/bin/brew"

echo "==> [1/7] Checking Homebrew on server..."
if ! ssh "$SERVER" "test -f $BREW"; then
    echo "    Homebrew not found at $BREW — installing now."
    echo "    Note: Homebrew install on macOS Monterey is non-interactive and takes a few minutes."
    ssh "$SERVER" '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

    # Verify Homebrew actually installed
    if ! ssh "$SERVER" "test -f $BREW"; then
        echo "ERROR: Homebrew installation failed — $BREW not found after install."
        echo "       SSH to the server and run the install manually:"
        echo "       /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    echo "    Homebrew installed at $BREW."
else
    echo "    Homebrew already installed at $BREW — skipping."
fi

echo ""
echo "==> [2/7] Installing nginx..."
echo "    NOTE: Homebrew has no pre-built bottle for nginx on macOS Monterey (x86_64)."
echo "    nginx will BUILD FROM SOURCE. Allow 10-20 minutes. Do not interrupt."
echo ""
ssh "$SERVER" "$BREW install nginx"
echo "    nginx installed."

echo ""
echo "==> [3/7] Creating web root /var/www/x402-network/..."
echo "    This uses sudo — you will be prompted for your server password."
ssh -t "$SERVER" "sudo mkdir -p /private/var/www/x402-network && sudo chown jameswisdom:staff /private/var/www/x402-network"

# Verify web root exists
if ssh "$SERVER" "test -d /var/www/x402-network && echo OK" | grep -q OK; then
    echo "    Web root /var/www/x402-network/ created and owned by jameswisdom."
else
    echo "ERROR: Web root /var/www/x402-network/ was not created."
    exit 1
fi

echo ""
echo "==> [4/7] Writing nginx site config..."
ssh "$SERVER" "cat > /tmp/x402-network.conf" << 'NGINXCONF'
server {
    listen 8888;
    server_name _;

    root /var/www/x402-network;
    index index.html;

    # SPA fallback — Astro client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Deny all dotfile paths — /.planning/, /.git/, /.env, etc.
    location ~ /\. {
        deny all;
        return 404;
    }

    # Security headers (HTTP only — no HSTS since not TLS)
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

    # Long-term immutable cache for fingerprinted Astro assets
    location /_astro/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # No-cache for HTML — always serve fresh
    location ~* \.html$ {
        add_header Cache-Control "no-cache";
    }
}
NGINXCONF

ssh -t "$SERVER" "sudo mkdir -p /usr/local/etc/nginx/servers && sudo mv /tmp/x402-network.conf /usr/local/etc/nginx/servers/x402-network.conf"
echo "    nginx site config written to /usr/local/etc/nginx/servers/x402-network.conf"

echo ""
echo "==> [5/7] Installing LaunchDaemon plist for boot-time autostart..."
echo "    This uses sudo — you may be prompted for your server password."
ssh "$SERVER" "cat > /tmp/homebrew.mxcl.nginx.plist" << 'PLIST'
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
PLIST

ssh -t "$SERVER" "sudo mv /tmp/homebrew.mxcl.nginx.plist /Library/LaunchDaemons/ && sudo chown root:wheel /Library/LaunchDaemons/homebrew.mxcl.nginx.plist"
echo "    LaunchDaemon plist installed at /Library/LaunchDaemons/homebrew.mxcl.nginx.plist"
echo "    (Port 8888 — AdGuard Home occupies port 80)"

echo ""
echo "==> [6/7] Validating nginx config and starting nginx..."
echo "    This uses sudo — you may be prompted for your server password."
ssh -t "$SERVER" "sudo /usr/local/opt/nginx/bin/nginx -t"
ssh -t "$SERVER" "sudo launchctl load -w /Library/LaunchDaemons/homebrew.mxcl.nginx.plist"
echo "    nginx config valid. nginx started via launchctl."

echo ""
echo "==> [7/7] Verifying nginx is serving on port 8888..."
# Brief pause for nginx to come up
sleep 2
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://10.0.0.2:8888/")
if [[ "$STATUS" == "200" || "$STATUS" == "403" || "$STATUS" == "404" ]]; then
    echo "PASS: nginx is responding on http://10.0.0.2:8888 (status: $STATUS)"
else
    echo "FAIL: nginx did not respond as expected (status: $STATUS)"
    echo "      Check server logs: ssh $SERVER 'sudo tail -20 /usr/local/var/log/nginx/error.log'"
    echo "      Validate config:   ssh $SERVER 'sudo /usr/local/opt/nginx/bin/nginx -t'"
    echo "      Check port 8888:   ssh $SERVER 'sudo lsof -i :8888'"
    exit 1
fi

echo ""
echo "Server setup complete. nginx is live at http://10.0.0.2:8888"
echo "Web root: /var/www/x402-network/ (empty — run deploy.sh next)"
echo ""
echo "Useful commands:"
echo "  Reload nginx after config changes:  ssh $SERVER 'sudo /usr/local/opt/nginx/bin/nginx -s reload'"
echo "  Stop nginx:                         ssh $SERVER 'sudo launchctl unload /Library/LaunchDaemons/homebrew.mxcl.nginx.plist'"
echo "  View error log:                     ssh $SERVER 'sudo tail -f /usr/local/var/log/nginx/error.log'"
