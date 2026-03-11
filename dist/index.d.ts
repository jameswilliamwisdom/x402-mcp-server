#!/usr/bin/env node
/**
 * x402 API Network — MCP Server
 *
 * Wraps the x402 API Network (screenshot, PDF extraction, crypto sentiment)
 * as agent-callable MCP tools with automatic USDC micropayment handling.
 *
 * Payment is handled transparently via x402-fetch when X402_PRIVATE_KEY
 * is configured. Without a key, only free test endpoints are available.
 */
export {};
