/**
 * Shared helpers, constants, and HTTP wrappers for the x402 MCP server.
 * Extracted for testability — all tool handlers import from here.
 */
export declare const APIS: {
    readonly screenshot: {
        readonly name: "Screenshot API";
        readonly baseUrl: "https://usdc-screenshot-api-production.up.railway.app";
        readonly price: "$0.01";
        readonly description: "Capture website screenshots as base64 images";
        readonly usesX402: true;
    };
    readonly pdf: {
        readonly name: "PDF Extraction API";
        readonly baseUrl: "https://pdf-api-production-cf1e.up.railway.app";
        readonly price: "$0.01";
        readonly description: "Extract text content from PDF documents";
        readonly usesX402: true;
    };
    readonly sentiment: {
        readonly name: "Crypto Sentiment API";
        readonly baseUrl: "https://crypto-sentiment-api-production-0ff4.up.railway.app";
        readonly price: "$0.01–$0.10";
        readonly description: "Real-time crypto market sentiment analysis";
        readonly usesX402: true;
    };
    readonly email: {
        readonly name: "Email API";
        readonly baseUrl: "https://x402-email-api-production.up.railway.app";
        readonly price: "$0.01";
        readonly description: "Send transactional emails via Resend";
        readonly usesX402: true;
    };
    readonly scraping: {
        readonly name: "Scraping API";
        readonly baseUrl: "https://x402-scraping-api-production.up.railway.app";
        readonly price: "$0.02";
        readonly description: "Scrape or crawl any URL and return structured JSON: markdown, links, tables, images, metadata";
        readonly usesX402: true;
    };
    readonly conversion: {
        readonly name: "Conversion API";
        readonly baseUrl: "https://x402-conversion-api-production.up.railway.app";
        readonly price: "$0.02";
        readonly description: "Convert files: image resize/reformat, CSV to JSON, HTML to PDF";
        readonly usesX402: true;
    };
    readonly search: {
        readonly name: "Search API";
        readonly baseUrl: "https://x402-search-api-production.up.railway.app";
        readonly price: "$0.01";
        readonly description: "Web search via Tavily — ranked results with title, URL, snippet, score";
        readonly usesX402: true;
    };
    readonly transcription: {
        readonly name: "Transcription API";
        readonly baseUrl: "https://transcribe.jameswisdom.ink";
        readonly price: "$0.05";
        readonly description: "Transcribe audio from any URL — auto language detection, word timestamps, 25MB/10min limits";
        readonly usesX402: true;
    };
};
export declare function getPrivateKey(): `0x${string}` | undefined;
export declare function resetPaidFetch(): void;
export declare function getPaidFetch(): typeof fetch;
export declare function textResult(data: unknown): {
    content: {
        type: "text";
        text: string;
    }[];
};
export declare function errorResult(message: string): {
    content: {
        type: "text";
        text: string;
    }[];
    isError: boolean;
};
export declare function apiGet(baseUrl: string, path: string, usePayment?: boolean): Promise<any>;
export declare function apiPost(baseUrl: string, path: string, body: Record<string, unknown>, usePayment?: boolean): Promise<any>;
export declare function checkHealth(baseUrl: string): Promise<{
    healthy: boolean;
    details?: unknown;
    error?: string;
}>;
