# Bismuth — x402 MCP Server

Pay-per-use APIs for AI agents, powered by the Bismuth (x402 API Network). One npm install, automatic USDC micropayments on Base.

[![License: MIT](https://img.shields.io/github/license/jameswilliamwisdom/x402-mcp-server)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
[![GitHub Stars](https://img.shields.io/github/stars/jameswilliamwisdom/x402-mcp-server?style=social)](https://github.com/jameswilliamwisdom/x402-mcp-server)

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `x402_network_info` | List all APIs with pricing and health status | Free |
| `x402_screenshot` | Capture any URL as a base64 image | $0.01 / capture |
| `x402_pdf_extract` | Extract text from a PDF via URL | $0.01 / extraction |
| `x402_sentiment` | Real-time sentiment analysis for a crypto coin | $0.01 / query |
| `x402_market_overview` | Broad crypto market sentiment overview | $0.05 / query |
| `x402_intelligence` | Multi-source crypto intelligence (CoinGecko, DeFiLlama, news, GitHub) | $0.10 / query |
| `x402_send_email` | Send transactional emails via Resend with CC, BCC, and file attachments | $0.01 / email |
| `x402_scrape_url` | Scrape any URL and return structured markdown, links, tables, metadata | $0.02 / scrape |
| `x402_convert_file` | Convert files: image resize/reformat, CSV to JSON, HTML to PDF, DOCX to PDF | $0.02 / conversion |
| `x402_web_search` | Search the web via Tavily with ranked results and optional AI answer | $0.01 / search |
| `x402_transcribe_audio` | Transcribe audio files with auto language detection and word timestamps | $0.05 / transcription |
| `x402_crawl_site` | Crawl a website via BFS and return per-page markdown, links, tables, images, metadata | $0.10 / crawl |

## What's New in 2.0.0

Three capability extensions and one new tool:
- **Shallow Site Crawl** — new `x402_crawl_site` tool: BFS crawl up to 15 pages from a seed URL
- **Email CC/BCC/Attachments** — `x402_send_email` now accepts cc, bcc, and base64 file attachments
- **DOCX to PDF** — `x402_convert_file` now supports type: "docx" for DOCX document conversion

## Quick Start — Free Mode

No wallet or private key needed. Add the server to your MCP client config:

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "x402-mcp-server"]
    }
  }
}
```

Free mode limitations:
- Screenshots limited to example.com, example.org, and httpbin.org
- PDF extraction limited to first 3 pages
- Sentiment returns mock data with real market structure
- Email returns a fake message ID (no delivery)
- Scraping returns fixture data (no live scraping)
- File conversion returns fixture data (no live conversion)
- Web search returns fixture results (no live search)
- Transcription returns fixture transcript (no live transcription)
- Site crawling returns fixture data (no live crawl)

## Quick Start — Paid Mode

Requires a Base wallet funded with USDC.

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "your-private-key-here"
      }
    }
  }
}
```

Never commit your private key. Store it in your system environment or a local `.env` file loaded by your shell.

You need USDC on the Base network. Base is an Ethereum L2 with low transaction fees. See the [full wallet setup guide](#) for detailed instructions.

## MCP Client Configs

Omit the `env` block entirely for free mode.

### Claude Desktop

Config file location:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "your-private-key-here"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add --transport stdio x402 -- npx -y x402-mcp-server
```

Then set `X402_PRIVATE_KEY` in your environment.

### Cursor

Config file: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "your-private-key-here"
      }
    }
  }
}
```

### Windsurf

Config file: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "x402-mcp-server"],
      "env": {
        "X402_PRIVATE_KEY": "your-private-key-here"
      }
    }
  }
}
```

## How It Works

1. Your AI agent calls a tool (e.g., `x402_screenshot`)
2. The MCP server makes an HTTP request to the API
3. The API responds with `402 Payment Required`
4. `x402-fetch` automatically signs a USDC payment on Base and retries
5. The API returns the result

The payment flow is handled by `x402-fetch` — your agent never needs to manage transactions directly.

## License

MIT
