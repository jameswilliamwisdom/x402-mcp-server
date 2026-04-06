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
import {
  APIS,
  getPrivateKey,
  apiGet,
  apiPost,
  checkHealth,
  textResult,
  errorResult,
} from "./helpers.js";

// ─── MCP Server ──────────────────────────────────────────────────────────────

export const server = new McpServer({
  name: "x402-api-network",
  version: "2.0.0",
});

// ─── Tool: x402_network_info (FREE) ─────────────────────────────────────────

server.tool(
  "x402_network_info",
  `List all APIs in the x402 API Network with pricing, status, and capabilities.
This tool is FREE — no payment required.

The x402 API Network provides pay-per-use APIs accepting USDC micropayments on Base (L2 Ethereum).`,
  {},
  async () => {
    const walletConfigured = !!getPrivateKey();
    const healthChecks = await Promise.allSettled(
      Object.entries(APIS).map(async ([key, api]) => {
        const health = await checkHealth(api.baseUrl);
        return { key, ...api, ...health };
      })
    );

    const results = healthChecks.map((r) => {
      if (r.status === "fulfilled") return r.value;
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
      apis: results.map((r: any) => ({
        id: r.key,
        name: r.name,
        status: r.healthy ? "online" : "offline",
        price: r.price,
        description: r.description,
        base_url: r.baseUrl,
        error: r.healthy ? undefined : r.error,
      })),
    });
  }
);

// ─── Tool: x402_screenshot ──────────────────────────────────────────────────

server.tool(
  "x402_screenshot",
  `Capture a screenshot of any URL and return it as a base64-encoded image.
Price: $0.01 USDC per capture (paid mode) | Free test: example.com, example.org, httpbin.org only.

Without X402_PRIVATE_KEY, only test domains are available.
With a wallet key, any URL can be captured via the paid endpoint.

Returns: base64 PNG/JPEG/WebP image data.`,
  {
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
  },
  async (params) => {
    const base = APIS.screenshot.baseUrl;

    try {
      const usePaid = !!getPrivateKey();
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
      } else {
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
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_pdf_extract ─────────────────────────────────────────────────

server.tool(
  "x402_pdf_extract",
  `Extract text content from a PDF document via URL.
Price: $0.01 USDC per extraction.

Uses PyMuPDF for fast text extraction. Handles multi-page PDFs.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: extracted text, page count, and metadata.`,
  {
    pdf_url: z.string().url().describe("URL of the PDF to extract text from"),
  },
  async (params) => {
    const base = APIS.pdf.baseUrl;

    try {
      const usePaid = !!getPrivateKey();
      const endpoint = usePaid ? "/extract" : "/test/extract";

      const data = await apiPost(
        base,
        endpoint,
        { url: params.pdf_url },
        usePaid
      );

      return textResult({
        mode: usePaid ? "paid" : "free_test",
        cost: usePaid ? "$0.01" : "free",
        ...data,
      });
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_sentiment ───────────────────────────────────────────────────

server.tool(
  "x402_sentiment",
  `Get real-time crypto sentiment analysis for a specific coin.
Price: $0.01 USDC per query.

Analyzes social media, news, and market data to produce sentiment scores.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: sentiment score (-1 to 1), confidence, sources, and analysis.`,
  {
    coin: z
      .string()
      .regex(/^[A-Z0-9]{1,10}$/i)
      .describe(
        "Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"
      ),
  },
  async (params) => {
    const base = APIS.sentiment.baseUrl;

    try {
      const usePaid = !!getPrivateKey();
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
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_market_overview ─────────────────────────────────────────────

server.tool(
  "x402_market_overview",
  `Get a broad crypto market sentiment overview covering major coins and trends.
Price: $0.05 USDC per query.

Provides aggregate sentiment across the crypto market.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: market-wide sentiment data, top movers, and trend analysis.`,
  {},
  async () => {
    const base = APIS.sentiment.baseUrl;

    try {
      const usePaid = !!getPrivateKey();
      const endpoint = usePaid ? "/market/overview" : "/test/market/overview";

      const data = await apiGet(base, endpoint, usePaid);
      return textResult({
        mode: usePaid ? "paid" : "free_test",
        cost: usePaid ? "$0.05" : "free",
        ...data,
      });
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_intelligence ─────────────────────────────────────────────────

server.tool(
  "x402_intelligence",
  `Get comprehensive multi-source intelligence analysis for a cryptocurrency.
Price: $0.10 USDC per query.

Aggregates data from CoinGecko (market), DeFiLlama (TVL/DeFi), CryptoPanic (news),
Fear & Greed Index (psychology), and GitHub (development activity).
All data synthesized by Claude AI for actionable insights.

This is the premium tier — use x402_sentiment ($0.01) for quick sentiment only.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: comprehensive analysis with market data, news, development activity, and AI synthesis.`,
  {
    coin: z
      .string()
      .regex(/^[A-Z0-9]{1,10}$/i)
      .describe(
        "Cryptocurrency ticker symbol (e.g., 'BTC', 'ETH', 'SOL')"
      ),
  },
  async (params) => {
    const base = APIS.sentiment.baseUrl;

    try {
      const usePaid = !!getPrivateKey();
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
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_send_email ─────────────────────────────────────────────────

server.tool(
  "x402_send_email",
  `Send a transactional email via Resend.
Price: $0.01 USDC per email (paid mode) | Free test: returns fixture data.

Supports plain text or HTML body, CC/BCC recipients, and file attachments (base64-encoded, max 25MB per file).
Per-wallet daily limit: 10 emails. Per-domain daily limit: 5 emails (applies to all recipients including CC/BCC).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: message_id from Resend.`,
  {
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
    cc: z.array(z.string().email()).optional()
        .describe("CC recipients — list of email addresses"),
    bcc: z.array(z.string().email()).optional()
        .describe("BCC recipients — list of email addresses"),
    attachments: z.array(z.object({
        filename: z.string().describe("Filename including extension (e.g. 'report.pdf')"),
        content: z.string().describe("Base64-encoded file content (max 25MB decoded)"),
        content_type: z.string().optional()
            .describe("MIME type — auto-derived from filename if omitted"),
    })).optional().describe("File attachments (base64-encoded, max 25MB pre-encoding per file)"),
  },
  async (params) => {
    const base = APIS.email.baseUrl;

    try {
      const usePaid = !!getPrivateKey();

      if (usePaid) {
        const payload: Record<string, unknown> = {
          to: params.to,
          subject: params.subject,
          body: params.body,
        };
        if (params.reply_to) payload.reply_to = params.reply_to;
        if (params.cc) payload.cc = params.cc;
        if (params.bcc) payload.bcc = params.bcc;
        if (params.attachments) payload.attachments = params.attachments;

        const data = await apiPost(base, "/send", payload, true);
        return textResult({
          mode: "paid",
          cost: "$0.01",
          ...data,
        });
      } else {
        const data = await apiGet(base, "/send/test");
        return textResult({
          mode: "free_test",
          note: "Free test — no email actually sent. Set X402_PRIVATE_KEY for real email delivery.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_scrape_url ──────────────────────────────────────────────────

server.tool(
  "x402_scrape_url",
  `Scrape a web page and return structured JSON with markdown content, links, tables, images, and metadata.
Price: $0.02 USDC per scrape (paid mode) | Free test: returns fixture data.

Supports JS-rendered pages via Playwright. Optional wait_for CSS selector for async SPA content.
Hard timeout: 8 seconds total (page load + selector wait combined).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: markdown text, extracted links, tables, images, page metadata, and success/failure status.`,
  {
    url: z.string().url().describe("URL to scrape (http/https, max 2048 chars)"),
    wait_for: z.string().max(500).optional()
      .describe("CSS selector to wait for before extracting (for SPAs, e.g. '.article-body')"),
  },
  async (params) => {
    const base = APIS.scraping.baseUrl;
    try {
      const usePaid = !!getPrivateKey();
      if (usePaid) {
        const payload: Record<string, unknown> = { url: params.url };
        if (params.wait_for) payload.wait_for = params.wait_for;
        const data = await apiPost(base, "/scrape", payload, true);
        return textResult({ mode: "paid", cost: "$0.02", ...data });
      } else {
        const data = await apiGet(base, "/scrape/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live scraping.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_convert_file ────────────────────────────────────────────────

server.tool(
  "x402_convert_file",
  `Convert files between formats — image resize/reformat, CSV to JSON, HTML to PDF, or DOCX to PDF.
Price: $0.02 USDC per conversion (paid mode) | Free test: returns fixture data.

Supported conversions:
- image: resize/reformat an image from a URL (Pillow) — outputs base64-encoded bytes
- csv: convert a CSV URL to JSON array
- html_pdf: render HTML from a URL to PDF — outputs base64-encoded bytes
- docx: convert a DOCX document URL to PDF — outputs base64-encoded bytes (mammoth + WeasyPrint, content-fidelity not layout-preserving)

Input limit: 10MB source file. Output limit: 8MB (before base64 encoding).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: base64-encoded output bytes with MIME type, or JSON array for csv type.`,
  {
    url: z.string().url().describe("URL of the file to convert (public, http/https, max 10MB)"),
    type: z.enum(["image", "csv", "html_pdf", "docx"])
      .describe("Conversion type: image (resize/reformat), csv (CSV to JSON), html_pdf (HTML to PDF), docx (DOCX to PDF)"),
    format: z.enum(["jpeg", "png", "webp", "gif"]).optional()
      .describe("Output image format (only for type='image', default: jpeg)"),
    width: z.number().int().min(1).max(8000).optional()
      .describe("Target width in pixels (only for type='image', preserves aspect ratio if height omitted)"),
    height: z.number().int().min(1).max(8000).optional()
      .describe("Target height in pixels (only for type='image', preserves aspect ratio if width omitted)"),
  },
  async (params) => {
    const base = APIS.conversion.baseUrl;
    try {
      const usePaid = !!getPrivateKey();
      if (usePaid) {
        const payload: Record<string, unknown> = { type: params.type, url: params.url };
        if (params.format !== undefined) payload.format = params.format;
        if (params.width !== undefined) payload.width = params.width;
        if (params.height !== undefined) payload.height = params.height;
        const data = await apiPost(base, "/convert", payload, true);
        return textResult({ mode: "paid", cost: "$0.02", ...data });
      } else {
        const data = await apiGet(base, "/convert/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live conversion.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_web_search ──────────────────────────────────────────────────

server.tool(
  "x402_web_search",
  `Search the web and return ranked results via Tavily — title, URL, snippet, and relevance score.
Price: $0.01 USDC per search (paid mode) | Free test: returns fixture data.

Optional synthesized answer summarizing results. Use include_domains/exclude_domains for focused research.
Per-wallet daily limit: 50 queries (resets midnight UTC).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: query, results array (title, url, snippet, score), optional answer field.`,
  {
    query: z.string().min(1).max(400).describe("Search query (max 400 chars)"),
    max_results: z.number().int().min(1).max(10).default(5)
      .describe("Number of results to return (1-10, default: 5)"),
    include_answer: z.boolean().default(false)
      .describe("Include a synthesized answer above the results (may be null if Tavily cannot synthesize)"),
    include_domains: z.array(z.string()).max(20).optional()
      .describe("Restrict results to these domains only (max 20)"),
    exclude_domains: z.array(z.string()).max(20).optional()
      .describe("Exclude these domains from results (max 20)"),
  },
  async (params) => {
    const base = APIS.search.baseUrl;
    try {
      const usePaid = !!getPrivateKey();
      if (usePaid) {
        const payload: Record<string, unknown> = {
          query: params.query,
          max_results: params.max_results,
          include_answer: params.include_answer,
        };
        if (params.include_domains) payload.include_domains = params.include_domains;
        if (params.exclude_domains) payload.exclude_domains = params.exclude_domains;
        const data = await apiPost(base, "/search", payload, true);
        return textResult({ mode: "paid", cost: "$0.01", ...data });
      } else {
        const data = await apiGet(base, "/search/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live web search.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_transcribe_audio ────────────────────────────────────────────

server.tool(
  "x402_transcribe_audio",
  `Transcribe an audio file from a URL using faster-whisper with auto language detection.
Price: $0.05 USDC per transcription (paid mode) | Free test: returns fixture data.

Supports: MP3, WAV, M4A, FLAC, OGG, and most audio formats.
Limits: 25MB file size, 10-minute duration. Payment is charged on download; duration refusals are still charged.
Note: transcription can take 30–120 seconds for longer files (CPU-based, requests queue serially).
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: transcript text, detected language, language confidence, duration, and segment or word timestamps.`,
  {
    url: z.string().url().describe("URL of the audio file to transcribe (public, http/https, max 25MB, max 10 min)"),
    language: z.string().optional()
      .describe("ISO 639-1 language hint (e.g. 'en', 'fr', 'es') — omit for auto-detection"),
    word_timestamps: z.boolean().default(false)
      .describe("Return word-level timestamps instead of segment-level (default: false)"),
  },
  async (params) => {
    const base = APIS.transcription.baseUrl;
    try {
      const usePaid = !!getPrivateKey();
      if (usePaid) {
        const payload: Record<string, unknown> = {
          url: params.url,
          word_timestamps: params.word_timestamps,
        };
        if (params.language) payload.language = params.language;
        const data = await apiPost(base, "/transcribe", payload, true);
        return textResult({ mode: "paid", cost: "$0.05", ...data });
      } else {
        const data = await apiGet(base, "/transcribe/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for real audio transcription.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Tool: x402_crawl_site ──────────────────────────────────────────────────

server.tool(
  "x402_crawl_site",
  `Crawl a website via BFS and return per-page extraction results (markdown, links, tables, images, metadata).
Price: $0.10 USDC per crawl (paid mode) | Free test: returns fixture data.

Crawls up to max_pages pages starting from the seed URL, up to max_depth link hops deep.
Same extraction pipeline as x402_scrape_url — each page returns markdown, links, tables, images, metadata.
Optional include_paths/exclude_paths glob filters (e.g. '/blog/*') restrict which URLs are followed.
Hard limits: max 15 pages, max depth 5. Response includes pages_requested, pages_crawled, pages_skipped.
Without X402_PRIVATE_KEY, only the free test endpoint is available.

Returns: seed_url, pages_requested, pages_crawled, pages_skipped, reasons_skipped, results array.`,
  {
    url: z.string().url()
      .describe("Seed URL to begin crawling (http/https, max 2048 chars)"),
    max_pages: z.number().int().min(1).max(15).default(10)
      .describe("Maximum pages to crawl (1-15, default: 10)"),
    max_depth: z.number().int().min(1).max(5).default(2)
      .describe("Maximum link depth from seed URL (1-5, default: 2)"),
    include_paths: z.array(z.string()).max(20).optional()
      .describe("Only follow URLs matching these path glob patterns (e.g. '/blog/*', max 20)"),
    exclude_paths: z.array(z.string()).max(20).optional()
      .describe("Skip URLs matching these path glob patterns (e.g. '/admin/*', max 20)"),
  },
  async (params) => {
    const base = APIS.scraping.baseUrl;
    try {
      const usePaid = !!getPrivateKey();
      if (usePaid) {
        const payload: Record<string, unknown> = {
          url: params.url,
          max_pages: params.max_pages,
          max_depth: params.max_depth,
        };
        if (params.include_paths) payload.include_paths = params.include_paths;
        if (params.exclude_paths) payload.exclude_paths = params.exclude_paths;
        const data = await apiPost(base, "/crawl", payload, true);
        return textResult({ mode: "paid", cost: "$0.10", ...data });
      } else {
        const data = await apiGet(base, "/crawl/test");
        return textResult({
          mode: "free_test",
          note: "Free test — returns fixture data. Set X402_PRIVATE_KEY for live crawling.",
          ...data,
        });
      }
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);

// ─── Start ───────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// Only auto-connect when run directly (not when imported for tests)
const isDirectRun =
  typeof process !== "undefined" &&
  process.argv[1] &&
  (process.argv[1].endsWith("/index.js") || process.argv[1].endsWith("/index.ts"));

if (isDirectRun) {
  main().catch((err) => {
    console.error("Fatal:", err);
    process.exit(1);
  });
}
