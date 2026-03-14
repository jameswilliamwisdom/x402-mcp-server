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
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { wrapFetchWithPayment } from "x402-fetch";
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base as baseChain } from "viem/chains";
// ─── API Endpoints ───────────────────────────────────────────────────────────
const APIS = {
    screenshot: {
        name: "Screenshot API",
        baseUrl: "https://usdc-screenshot-api-production.up.railway.app",
        price: "$0.01",
        description: "Capture website screenshots as base64 images",
        // v2.1.0 supports x402 via GET /screenshot with X-Payment header
        usesX402: true,
    },
    pdf: {
        name: "PDF Extraction API",
        baseUrl: "https://pdf-api-production-cf1e.up.railway.app",
        price: "$0.01",
        description: "Extract text content from PDF documents",
        usesX402: true,
    },
    sentiment: {
        name: "Crypto Sentiment API",
        baseUrl: "https://crypto-sentiment-api-production-0ff4.up.railway.app",
        price: "$0.01–$0.10",
        description: "Real-time crypto market sentiment analysis",
        usesX402: true,
    },
    email: {
        name: "Email API",
        baseUrl: "https://x402-email-api-production.up.railway.app",
        price: "$0.01",
        description: "Send transactional emails via Resend",
        usesX402: true,
    },
};
// ─── Config ──────────────────────────────────────────────────────────────────
const PRIVATE_KEY = process.env.X402_PRIVATE_KEY;
// ─── Payment-wrapped fetch ──────────────────────────────────────────────────
// Use `any` for x402 interop — their types don't perfectly align with viem's strict generics
let _paidFetch = null;
let _walletClient = null;
function getPaidFetch() {
    if (_paidFetch)
        return _paidFetch;
    if (!PRIVATE_KEY) {
        throw new Error("X402_PRIVATE_KEY not configured. Set it to enable paid API access.");
    }
    const account = privateKeyToAccount(PRIVATE_KEY);
    _walletClient = createWalletClient({
        account,
        chain: baseChain,
        transport: http(),
    });
    // maxValue: 0.10 USDC (100000 in 6-decimal units) — safety cap per request
    _paidFetch = wrapFetchWithPayment(fetch, _walletClient, BigInt(100000));
    return _paidFetch;
}
// ─── Helpers ─────────────────────────────────────────────────────────────────
function textResult(data) {
    const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    return { content: [{ type: "text", text }] };
}
function errorResult(message) {
    return {
        content: [{ type: "text", text: `Error: ${message}` }],
        isError: true,
    };
}
async function apiGet(baseUrl, path, usePayment = false) {
    const f = usePayment ? getPaidFetch() : fetch;
    const res = await f(`${baseUrl}${path}`);
    if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`API ${res.status}: ${body}`);
    }
    return res.json();
}
async function apiPost(baseUrl, path, body, usePayment = false) {
    const f = usePayment ? getPaidFetch() : fetch;
    const res = await f(`${baseUrl}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json();
}
async function checkHealth(baseUrl) {
    try {
        const res = await fetch(`${baseUrl}/health`, {
            signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
            const data = await res.json();
            return { healthy: true, details: data };
        }
        // Fallback to /
        const rootRes = await fetch(`${baseUrl}/`, {
            signal: AbortSignal.timeout(5000),
        });
        if (rootRes.ok) {
            const data = await rootRes.json();
            return { healthy: true, details: data };
        }
        return { healthy: false, error: `HTTP ${res.status}` };
    }
    catch (err) {
        return { healthy: false, error: err.message };
    }
}
// ─── MCP Server ──────────────────────────────────────────────────────────────
const server = new McpServer({
    name: "x402-api-network",
    version: "1.0.0",
});
// ─── Tool: x402_network_info (FREE) ─────────────────────────────────────────
server.tool("x402_network_info", `List all APIs in the x402 API Network with pricing, status, and capabilities.
This tool is FREE — no payment required.

The x402 API Network provides pay-per-use APIs accepting USDC micropayments on Base (L2 Ethereum).`, {}, async () => {
    const walletConfigured = !!PRIVATE_KEY;
    const healthChecks = await Promise.allSettled(Object.entries(APIS).map(async ([key, api]) => {
        const health = await checkHealth(api.baseUrl);
        return { key, ...api, ...health };
    }));
    const results = healthChecks.map((r) => {
        if (r.status === "fulfilled")
            return r.value;
        return {
            key: "unknown",
            name: "Unknown",
            healthy: false,
            error: "Check failed",
        };
    });
    return textResult({
        network: "x402 API Network",
        blockchain: "Base (L2 Ethereum)",
        token: "USDC",
        wallet_configured: walletConfigured,
        payment_mode: walletConfigured
            ? "Automatic x402 payments enabled"
            : "Free test endpoints only — set X402_PRIVATE_KEY for paid access",
        apis: results.map((r) => ({
            id: r.key,
            name: r.name,
            status: r.healthy ? "online" : "offline",
            price: r.price,
            description: r.description,
            base_url: r.baseUrl,
            error: r.healthy ? undefined : r.error,
        })),
    });
});
// ─── Tool: x402_screenshot ──────────────────────────────────────────────────
server.tool("x402_screenshot", `Capture a screenshot of any URL and return it as a base64-encoded image.
Price: $0.01 USDC per capture (paid mode) | Free test: example.com, example.org, httpbin.org only.

Without X402_PRIVATE_KEY, only test domains are available.
With a wallet key, any URL can be captured via the paid endpoint.

Returns: base64 PNG/JPEG/WebP image data.`, {
    url: z.string().url().describe("URL to capture (full URL including https://)"),
    width: z
        .number()
        .int()
        .min(320)
        .max(3840)
        .default(1280)
        .describe("Viewport width in pixels (default: 1280)"),
    height: z
        .number()
        .int()
        .min(240)
        .max(2160)
        .default(720)
        .describe("Viewport height in pixels (default: 720)"),
    full_page: z
        .boolean()
        .default(false)
        .describe("Capture the full scrollable page (default: false)"),
    format: z
        .enum(["png", "jpeg", "webp"])
        .default("png")
        .describe("Image format (default: png)"),
}, async (params) => {
    const base = APIS.screenshot.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        const query = new URLSearchParams({
            url: params.url,
            width: String(params.width),
            height: String(params.height),
            full_page: String(params.full_page),
            format: params.format,
        });
        if (usePaid) {
            // x402 paid mode — GET /screenshot returns 402, x402-fetch handles payment
            const data = await apiGet(base, `/screenshot?${query}`, true);
            return textResult({
                mode: "paid",
                cost: "$0.01",
                ...data,
            });
        }
        else {
            // Free test mode — limited to example.com, example.org, httpbin.org
            const testQuery = new URLSearchParams({
                url: params.url,
                width: String(params.width),
                height: String(params.height),
            });
            const data = await apiGet(base, `/test/screenshot?${testQuery}`);
            return textResult({
                mode: "free_test",
                note: "Free test — limited to example.com, example.org, httpbin.org. Set X402_PRIVATE_KEY for any URL.",
                ...data,
            });
        }
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Tool: x402_pdf_extract ─────────────────────────────────────────────────
server.tool("x402_pdf_extract", `Extract text content from a PDF document via URL.
Price: $0.01 USDC per extraction.

Uses PyMuPDF for fast text extraction. Handles multi-page PDFs.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: extracted text, page count, and metadata.`, {
    pdf_url: z.string().url().describe("URL of the PDF to extract text from"),
}, async (params) => {
    const base = APIS.pdf.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        const endpoint = usePaid ? "/extract" : "/test/extract";
        const data = await apiPost(base, endpoint, { url: params.pdf_url }, usePaid);
        return textResult({
            mode: usePaid ? "paid" : "free_test",
            cost: usePaid ? "$0.01" : "free",
            ...data,
        });
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Tool: x402_sentiment ───────────────────────────────────────────────────
server.tool("x402_sentiment", `Get real-time crypto sentiment analysis for a specific coin.
Price: $0.01 USDC per query.

Analyzes social media, news, and market data to produce sentiment scores.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: sentiment score (-1 to 1), confidence, sources, and analysis.`, {
    coin: z
        .string()
        .regex(/^[A-Z0-9]{1,10}$/i)
        .describe("Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"),
}, async (params) => {
    const base = APIS.sentiment.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        const endpoint = usePaid
            ? `/sentiment/${params.coin.toLowerCase()}`
            : `/test/sentiment/${params.coin.toLowerCase()}`;
        const data = await apiGet(base, endpoint, usePaid);
        return textResult({
            mode: usePaid ? "paid" : "free_test",
            cost: usePaid ? "$0.01" : "free",
            coin: params.coin.toUpperCase(),
            ...data,
        });
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Tool: x402_market_overview ─────────────────────────────────────────────
server.tool("x402_market_overview", `Get a broad crypto market sentiment overview covering major coins and trends.
Price: $0.05 USDC per query.

Provides aggregate sentiment across the crypto market.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: market-wide sentiment data, top movers, and trend analysis.`, {}, async () => {
    const base = APIS.sentiment.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        const endpoint = usePaid ? "/market/overview" : "/test/market/overview";
        const data = await apiGet(base, endpoint, usePaid);
        return textResult({
            mode: usePaid ? "paid" : "free_test",
            cost: usePaid ? "$0.05" : "free",
            ...data,
        });
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Tool: x402_intelligence ─────────────────────────────────────────────────
server.tool("x402_intelligence", `Get comprehensive multi-source intelligence analysis for a cryptocurrency.
Price: $0.10 USDC per query.

Aggregates data from CoinGecko (market), DeFiLlama (TVL/DeFi), CryptoPanic (news),
Fear & Greed Index (psychology), and GitHub (development activity).
All data synthesized by Claude AI for actionable insights.

This is the premium tier — use x402_sentiment ($0.01) for quick sentiment only.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: comprehensive analysis with market data, news, development activity, and AI synthesis.`, {
    coin: z
        .string()
        .regex(/^[A-Z0-9]{1,10}$/i)
        .describe("Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"),
}, async (params) => {
    const base = APIS.sentiment.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        const endpoint = usePaid
            ? `/intelligence/${params.coin.toLowerCase()}`
            : `/test/intelligence/${params.coin.toLowerCase()}`;
        const data = await apiGet(base, endpoint, usePaid);
        return textResult({
            mode: usePaid ? "paid" : "free_test",
            cost: usePaid ? "$0.10" : "free",
            coin: params.coin.toUpperCase(),
            ...data,
        });
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Tool: x402_send_email ─────────────────────────────────────────────────
server.tool("x402_send_email", `Send a transactional email via Resend.
Price: $0.01 USDC per email.

Supports plain text or HTML body. Per-wallet daily limit: 10 emails. Per-domain daily limit: 5 emails.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: message_id from Resend.`, {
    to: z.string().email().describe("Recipient email address"),
    subject: z
        .string()
        .min(1)
        .max(998)
        .describe("Email subject (max 998 chars)"),
    body: z
        .string()
        .min(1)
        .max(102400)
        .describe("Email body — HTML or plain text (max 100 KB)"),
    reply_to: z
        .string()
        .email()
        .optional()
        .describe("Optional reply-to address"),
}, async (params) => {
    const base = APIS.email.baseUrl;
    try {
        const usePaid = !!PRIVATE_KEY;
        if (usePaid) {
            const payload = {
                to: params.to,
                subject: params.subject,
                body: params.body,
            };
            if (params.reply_to)
                payload.reply_to = params.reply_to;
            const data = await apiPost(base, "/send", payload, true);
            return textResult({
                mode: "paid",
                cost: "$0.01",
                ...data,
            });
        }
        else {
            const data = await apiGet(base, "/send/test");
            return textResult({
                mode: "free_test",
                note: "Free test — no email actually sent. Set X402_PRIVATE_KEY for real email delivery.",
                ...data,
            });
        }
    }
    catch (err) {
        return errorResult(err.message);
    }
});
// ─── Start ───────────────────────────────────────────────────────────────────
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
main().catch((err) => {
    console.error("Fatal:", err);
    process.exit(1);
});
