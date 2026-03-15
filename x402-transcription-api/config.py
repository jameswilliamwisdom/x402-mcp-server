# Audio limits
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25MB
MAX_DURATION_SECONDS = 600           # 10 minutes

# Transcription
WHISPER_MODEL = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_CPU_THREADS = 4              # Match physical cores: sysctl -n hw.physicalcpu
TRANSCRIPTION_TIMEOUT = 300          # seconds

# Pricing
PRICE_PER_REQUEST = "$0.05"

# Rate limiting
FREE_ENDPOINT_RATE = "100/hour"      # Per-IP for /transcribe/test
