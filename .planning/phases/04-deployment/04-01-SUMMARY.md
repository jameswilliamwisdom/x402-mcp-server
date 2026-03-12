# Plan 04-01 Summary: Server Setup

**Status:** Complete
**Completed:** 2026-03-12

## What was done

Provisioned home Mac server (10.0.0.2, macOS Monterey x86_64) for hosting the x402 brand site:

1. **Homebrew** — installed on Intel Mac at `/usr/local/bin/brew` (manual install required due to TTY/sudo constraint)
2. **nginx** — installed via Homebrew (source compile, no bottle for Monterey)
3. **Web root** — created `/var/www/x402-network/` owned by `jameswisdom:staff`
4. **nginx config** — custom server block in `/usr/local/etc/nginx/servers/x402-network.conf` with SPA fallback, dotfile deny, security headers, gzip, asset caching
5. **LaunchDaemon** — boot-time autostart via `/Library/LaunchDaemons/homebrew.mxcl.nginx.plist`
6. **Minimal nginx.conf** — replaced Homebrew default (removed conflicting port 8080 server block)

## Issues encountered

- **Port 80 occupied by AdGuard Home** — switched to port 8888
- **Homebrew installer needs interactive TTY** — user installed manually via SSH
- **`/usr/local/etc/nginx/servers/` not created by Homebrew** — added `mkdir -p` to script
- **`/usr/local/var/run/nginx/client_body_temp` missing** — created manually
- **Default nginx.conf binds port 8080 (already in use)** — replaced with minimal config that only includes `servers/*`

## Artifacts

- `site/setup-server.sh` — idempotent server provisioning script (committed)

## Verification

- `curl -s -o /dev/null -w "%{http_code}" http://10.0.0.2:8888/` → 403 (empty web root, nginx responding)
