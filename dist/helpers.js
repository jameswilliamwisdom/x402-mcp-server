/**
 * Shared helpers, constants, and HTTP wrappers for the x402 MCP server.
 * Extracted for testability — all tool handlers import from here.
 */
import { wrapFetchWithPayment } from "x402-fetch";
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base as baseChain } from "viem/chains";
// ─── API Endpoints ───────────────────────────────────────────────────────────
export const APIS = {
    screenshot: {
        name: "Screenshot API",
        baseUrl: "https://usdc-screenshot-api-production.up.railway.app",
        price: "$0.01",
        description: "Capture website screenshots as base64 images",
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
    scraping: {
        name: "Scraping API",
        baseUrl: "https://x402-scraping-api-production.up.railway.app",
        price: "$0.02",
        description: "Scrape or crawl any URL and return structured JSON: markdown, links, tables, images, metadata",
        usesX402: true,
    },
    conversion: {
        name: "Conversion API",
        baseUrl: "https://x402-conversion-api-production.up.railway.app",
        price: "$0.02",
        description: "Convert files: image resize/reformat, CSV to JSON, HTML to PDF",
        usesX402: true,
    },
    search: {
        name: "Search API",
        baseUrl: "https://x402-search-api-production.up.railway.app",
        price: "$0.01",
        description: "Web search via Tavily — ranked results with title, URL, snippet, score",
        usesX402: true,
    },
    transcription: {
        name: "Transcription API",
        baseUrl: "https://transcribe.jameswisdom.ink",
        price: "$0.05",
        description: "Transcribe audio from any URL — auto language detection, word timestamps, 25MB/10min limits",
        usesX402: true,
    },
};
// ─── Config ──────────────────────────────────────────────────────────────────
export function getPrivateKey() {
    return process.env.X402_PRIVATE_KEY;
}
// ─── Payment-wrapped fetch ──────────────────────────────────────────────────
let _paidFetch = null;
let _walletClient = null;
export function resetPaidFetch() {
    _paidFetch = null;
    _walletClient = null;
}
export function getPaidFetch() {
    if (_paidFetch)
        return _paidFetch;
    const key = getPrivateKey();
    if (!key) {
        throw new Error("X402_PRIVATE_KEY not configured. Set it to enable paid API access.");
    }
    const account = privateKeyToAccount(key);
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
export function textResult(data) {
    const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    return { content: [{ type: "text", text }] };
}
export function errorResult(message) {
    return {
        content: [{ type: "text", text: `Error: ${message}` }],
        isError: true,
    };
}
export async function apiGet(baseUrl, path, usePayment = false) {
    const f = usePayment ? getPaidFetch() : fetch;
    const res = await f(`${baseUrl}${path}`);
    if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`API ${res.status}: ${body}`);
    }
    return res.json();
}
export async function apiPost(baseUrl, path, body, usePayment = false) {
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
export async function checkHealth(baseUrl) {
    try {
        const res = await fetch(`${baseUrl}/health`, {
            signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
            const data = await res.json();
            return { healthy: true, details: data };
        }
        // Fallback to /
        const rootRes = await fetch(`${baseUrl}/`, {
            signal: AbortSignal.timeout(3000),
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
