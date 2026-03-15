#!/usr/bin/env bash
# deploy.sh — Home server deployment script for x402-transcription-api
#
# Run this from the x402-transcription-api directory on the home server:
#   cd x402-transcription-api && chmod +x deploy.sh && ./deploy.sh
#
# What this does:
#   1. Platform + architecture checks
#   2. CPU core check (for WHISPER_CPU_THREADS validation)
#   3. ffmpeg/ffprobe check (installs via Homebrew if missing)
#   4. Python venv creation
#   5. pip install -r requirements.txt
#   6. Whisper model download test (~466MB on first run)
#   7. launchd plist installation (with __SERVICE_DIR__ placeholder replaced)
#   8. Service load via launchctl
#   9. Health check verification
#  10. Cloudflare Tunnel setup instructions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$SCRIPT_DIR"
PLIST_NAME="com.x402.transcription"
PLIST_SRC="$SERVICE_DIR/launchd/$PLIST_NAME.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME.plist"

echo "=========================================="
echo "x402 Transcription API — Deploy Script"
echo "=========================================="
echo ""

# ---------------------------------------------------------------------------
# Step 1: Platform check
# ---------------------------------------------------------------------------
echo "[1/10] Checking platform..."
OS="$(uname -s)"
if [ "$OS" != "Darwin" ]; then
  echo "ERROR: This service is designed for macOS (launchd). Detected: $OS"
  echo "For Linux deployments, use a systemd unit file instead."
  exit 1
fi
echo "  OK — macOS detected"

# ---------------------------------------------------------------------------
# Step 2: Architecture check
# ---------------------------------------------------------------------------
echo "[2/10] Checking architecture..."
ARCH="$(uname -m)"
if [ "$ARCH" != "x86_64" ]; then
  echo "  WARNING: Expected x86_64 (Intel), got: $ARCH"
  echo "  faster-whisper int8 CPU mode is optimised for Intel x86_64."
  echo "  On Apple Silicon (arm64) you may want to use the mlx-whisper variant instead."
  echo "  Continuing anyway — faster-whisper will still work on arm64."
else
  echo "  OK — Intel x86_64"
fi

# ---------------------------------------------------------------------------
# Step 3: CPU core check
# ---------------------------------------------------------------------------
echo "[3/10] Checking CPU cores for WHISPER_CPU_THREADS..."
PHYSICAL_CORES="$(sysctl -n hw.physicalcpu 2>/dev/null || echo '?')"
echo "  Physical CPU cores: $PHYSICAL_CORES"
echo "  config.py currently sets WHISPER_CPU_THREADS = 4"
if [ "$PHYSICAL_CORES" != "4" ] && [ "$PHYSICAL_CORES" != "?" ]; then
  echo "  ACTION REQUIRED: Edit x402-transcription-api/config.py and set:"
  echo "    WHISPER_CPU_THREADS = $PHYSICAL_CORES"
  echo "  Setting cpu_threads above physical core count causes OOM (P2)."
  echo "  Press Enter to continue anyway, or Ctrl-C to abort and fix config.py first."
  read -r
else
  echo "  OK — cpu_threads=4 matches physical cores (or could not verify)"
fi

# ---------------------------------------------------------------------------
# Step 4: ffmpeg/ffprobe check
# ---------------------------------------------------------------------------
echo "[4/10] Checking ffmpeg/ffprobe..."
if command -v ffprobe &>/dev/null; then
  echo "  OK — ffprobe found at: $(which ffprobe)"
else
  echo "  ffprobe not found. Installing via Homebrew (required by faster-whisper's PyAV)..."
  if command -v brew &>/dev/null; then
    brew install ffmpeg
    echo "  OK — ffmpeg installed"
  else
    echo "  WARNING: Homebrew not found. Install ffmpeg manually: https://ffmpeg.org/download.html"
    echo "  Without ffmpeg, PyAV may fail on some audio container formats."
    echo "  Press Enter to continue anyway..."
    read -r
  fi
fi

# ---------------------------------------------------------------------------
# Step 5: Create Python venv
# ---------------------------------------------------------------------------
echo "[5/10] Creating Python venv..."
if [ -d "$SERVICE_DIR/.venv" ]; then
  echo "  .venv already exists — skipping creation"
else
  python3 -m venv "$SERVICE_DIR/.venv"
  echo "  OK — .venv created at $SERVICE_DIR/.venv"
fi

# ---------------------------------------------------------------------------
# Step 6: Install dependencies
# ---------------------------------------------------------------------------
echo "[6/10] Installing dependencies from requirements.txt..."
"$SERVICE_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$SERVICE_DIR/.venv/bin/pip" install -r "$SERVICE_DIR/requirements.txt"
echo "  OK — dependencies installed"

# ---------------------------------------------------------------------------
# Step 7: Test model download (first run downloads ~466MB)
# ---------------------------------------------------------------------------
echo "[7/10] Testing faster-whisper model download..."
echo "  (First run downloads ~466MB to ~/.cache/huggingface/ — this may take a few minutes)"
"$SERVICE_DIR/.venv/bin/python" -c "
from faster_whisper import WhisperModel
import warnings
warnings.filterwarnings('ignore', message='FP16 is not supported')
m = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
print('  OK — WhisperModel(small, cpu, int8) loaded successfully')
del m
"
echo "  OK — model loaded and released"

# ---------------------------------------------------------------------------
# Step 8: Install launchd plist
# ---------------------------------------------------------------------------
echo "[8/10] Installing launchd plist..."
mkdir -p "$LAUNCH_AGENTS_DIR"

# Replace __SERVICE_DIR__ placeholder with the actual absolute service path
sed "s|__SERVICE_DIR__|$SERVICE_DIR|g" "$PLIST_SRC" > "$PLIST_DEST"
echo "  Plist installed to: $PLIST_DEST"
echo ""
echo "  *** ACTION REQUIRED: Fill in credentials in the plist ***"
echo "  Edit: nano $PLIST_DEST"
echo "  Replace FILL_IN_AT_DEPLOY for:"
echo "    - PAY_TO_ADDRESS  (same USDC wallet as Railway services)"
echo "    - CDP_API_KEY_ID  (Coinbase Developer Platform API key)"
echo "    - CDP_API_KEY_SECRET (Coinbase Developer Platform API secret)"
echo ""
echo "  Press Enter after saving the plist with real credentials..."
read -r

# Verify env vars were actually filled in
if grep -q "FILL_IN_AT_DEPLOY" "$PLIST_DEST"; then
  echo "  ERROR: Plist still contains FILL_IN_AT_DEPLOY placeholders."
  echo "  Edit $PLIST_DEST and replace all three values, then re-run this script."
  exit 1
fi
echo "  OK — credentials set"

# ---------------------------------------------------------------------------
# Step 9: Load service and health check
# ---------------------------------------------------------------------------
echo "[9/10] Loading service via launchctl..."
# Unload first if already loaded (idempotent)
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "  Loaded — waiting 10 seconds for service to start and model to load..."
sleep 10

echo "  Checking local health endpoint..."
HEALTH_RESPONSE="$(curl -s http://localhost:8889/health || echo 'CURL_FAILED')"
if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
  echo "  OK — Health response: $HEALTH_RESPONSE"
else
  echo "  WARNING: Health check failed or service not yet ready."
  echo "  Response: $HEALTH_RESPONSE"
  echo "  The model takes ~30-60 seconds to load on first start. Check logs:"
  echo "    tail -f /tmp/com.x402.transcription.stderr.log"
  echo "  Check service status: launchctl list | grep x402"
fi

echo ""
echo "  Checking test fixture endpoint..."
TEST_RESPONSE="$(curl -s http://localhost:8889/transcribe/test || echo 'CURL_FAILED')"
if echo "$TEST_RESPONSE" | grep -q '"transcript"'; then
  echo "  OK — Test fixture response received"
else
  echo "  WARNING: Test endpoint not responding. Check logs as above."
fi

# ---------------------------------------------------------------------------
# Step 10: Cloudflare Tunnel setup instructions
# ---------------------------------------------------------------------------
echo ""
echo "[10/10] Cloudflare Tunnel Setup"
echo "========================================"
echo ""
echo "IMPORTANT: Verify auto-login is enabled (service needs active GUI session):"
echo "  System Preferences -> Users & Groups -> Login Options -> Automatic Login"
echo ""
echo "Install and configure cloudflared:"
echo ""
echo "  # Install"
echo "  brew install cloudflared"
echo ""
echo "  # Authenticate with your Cloudflare account (opens browser)"
echo "  cloudflared tunnel login"
echo ""
echo "  # Create the named tunnel"
echo "  cloudflared tunnel create transcription-api"
echo "  # -> Note the UUID printed (e.g. a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
echo ""
echo "  # Create DNS CNAME for transcribe.jameswisdom.ink"
echo "  cloudflared tunnel route dns transcription-api transcribe.jameswisdom.ink"
echo ""
echo "  # Edit the cloudflared config template:"
echo "  #   Replace __TUNNEL_UUID__ with the UUID from 'tunnel create'"
echo "  #   Replace __HOME_DIR__ with: \$HOME  (e.g. /Users/james)"
echo "  cp $SERVICE_DIR/cloudflared/config.yml ~/.cloudflared/config.yml"
echo "  nano ~/.cloudflared/config.yml"
echo ""
echo "  # Validate ingress rules"
echo "  cloudflared tunnel ingress validate"
echo ""
echo "  # Test tunnel manually first"
echo "  cloudflared tunnel run transcription-api"
echo "  # Verify in another terminal: curl -s https://transcribe.jameswisdom.ink/health"
echo ""
echo "  # Install as system service (optional — runs at boot, not just login)"
echo "  sudo cloudflared service install"
echo ""
echo "  # CRITICAL (P10 — known cloudflared bug): After service install, inspect:"
echo "  #   sudo cat /Library/LaunchDaemons/com.cloudflare.cloudflared.plist"
echo "  # Verify ProgramArguments contains <string>tunnel</string><string>run</string>"
echo "  # If missing, add them before: sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist"
echo ""
echo "========================================"
echo "Deployment complete. Summary:"
echo "  Service:    launchctl list | grep x402"
echo "  Local:      curl -s http://localhost:8889/health"
echo "  Public:     curl -s https://transcribe.jameswisdom.ink/health"
echo "  Logs:       tail -f /tmp/com.x402.transcription.stderr.log"
echo "========================================"
