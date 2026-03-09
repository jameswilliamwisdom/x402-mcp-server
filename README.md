# x402 MCP Server

MCP server for the **x402 API Network** — screenshot capture, PDF extraction, and crypto intelligence tools with automatic USDC micropayments on Base.

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `x402_network_info` | List all APIs, pricing, and health status | Free |
| `x402_screenshot` | Capture any URL as base64 image | $0.01 |
| `x402_pdf_extract` | Extract text from PDF via file upload | $0.01 |
| `x402_sentiment` | AI sentiment analysis for a cryptocurrency | $0.01 |
| `x402_market_overview` | Broad crypto market sentiment | $0.05 |
| `x402_intelligence` | Comprehensive multi-source crypto analysis | $0.10 |

## Quick Start

### Claude Code

Add to your Claude Code MCP config (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "x402": {
      "command": "node",
      "args": ["/path/to/x402-mcp-server/dist/index.js"],
      "env": {
        "X402_PRIVATE_KEY": "0x..."
      }
    }
  }
}
```

### Without Payment (Free Test Mode)

Omit `X402_PRIVATE_KEY` to use free test endpoints:
- Screenshots limited to example.com, example.org, httpbin.org
- PDF extraction limited to first 3 pages
- Sentiment returns mock data with real market info

### With Payment

Set `X402_PRIVATE_KEY` to an Ethereum private key with USDC on Base. Payments are handled automatically via the x402 protocol — no manual transactions needed.

## How It Works

1. Your agent calls a tool (e.g., `x402_screenshot`)
2. The MCP server makes an HTTP request to the API
3. The API responds with `402 Payment Required`
4. `x402-fetch` automatically signs a USDC payment and retries
5. The API returns the result

## APIs

- **Screenshot API** — `usdc-screenshot-api-production.up.railway.app`
- **PDF Extraction API** — `pdf-api-production-cf1e.up.railway.app`
- **Crypto Intelligence API** — `crypto-sentiment-api-production-0ff4.up.railway.app`

## Build

```bash
npm install
npm run build
```

## License

MIT
