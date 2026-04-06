import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { server } from "../index.js";

// ─── Test Harness ───────────────────────────────────────────────────────────

let client: Client;

function mockFetchResponse(body: unknown, opts: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = opts;
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
  };
}

/** Connect once for all tests — the server is a singleton */
beforeAll(async () => {
  delete process.env.X402_PRIVATE_KEY;

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });

  await server.connect(serverTransport);
  await client.connect(clientTransport);
});

beforeEach(() => {
  delete process.env.X402_PRIVATE_KEY;
});

afterAll(async () => {
  await client.close();
});

/** Call a tool and parse the JSON from its text response */
async function callTool(name: string, args: Record<string, unknown> = {}) {
  const result = await client.callTool({ name, arguments: args });
  const text = (result.content as any[])[0]?.text;
  try {
    return { parsed: JSON.parse(text), raw: text, isError: result.isError };
  } catch {
    return { parsed: null, raw: text, isError: result.isError };
  }
}

// ─── Tool: x402_network_info ────────────────────────────────────────────────

describe("x402_network_info", () => {
  it("returns all 8 APIs with health status (free mode)", async () => {
    // Mock all health checks as healthy
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "ok" }),
      })
    );

    const { parsed } = await callTool("x402_network_info");
    expect(parsed.network).toBe("x402 API Network");
    expect(parsed.wallet_configured).toBe(false);
    expect(parsed.apis).toHaveLength(8);
    expect(parsed.apis[0].status).toBe("online");
  });

  it("marks APIs as offline when health checks fail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("ECONNREFUSED"))
    );

    const { parsed } = await callTool("x402_network_info");
    expect(parsed.apis.every((a: any) => a.status === "offline")).toBe(true);
  });
});

// ─── Tool: x402_screenshot ──────────────────────────────────────────────────

describe("x402_screenshot", () => {
  it("uses free test endpoint when no private key", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      mockFetchResponse({ image: "base64data", format: "png" })
    );
    vi.stubGlobal("fetch", fetcher);

    const { parsed } = await callTool("x402_screenshot", {
      url: "https://example.com",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.image).toBe("base64data");
    // Should hit /test/screenshot
    const calledUrl = fetcher.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/test/screenshot");
  });

  it("returns error on API failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse("Timeout", { ok: false, status: 504 })
      )
    );

    const { raw, isError } = await callTool("x402_screenshot", {
      url: "https://example.com",
    });
    expect(isError).toBe(true);
    expect(raw).toContain("504");
  });
});

// ─── Tool: x402_pdf_extract ─────────────────────────────────────────────────

describe("x402_pdf_extract", () => {
  it("extracts PDF via free test endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      mockFetchResponse({ text: "Hello PDF", pages: 3 })
    );
    vi.stubGlobal("fetch", fetcher);

    const { parsed } = await callTool("x402_pdf_extract", {
      pdf_url: "https://example.com/doc.pdf",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.text).toBe("Hello PDF");
    expect(parsed.pages).toBe(3);
    // Should POST to /test/extract
    const [url, opts] = fetcher.mock.calls[0];
    expect(url).toContain("/test/extract");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ url: "https://example.com/doc.pdf" });
  });
});

// ─── Tool: x402_sentiment ───────────────────────────────────────────────────

describe("x402_sentiment", () => {
  it("returns sentiment for a coin (free mode)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({ score: 0.72, confidence: 0.85 })
      )
    );

    const { parsed } = await callTool("x402_sentiment", { coin: "BTC" });
    expect(parsed.mode).toBe("free_test");
    expect(parsed.coin).toBe("BTC");
    expect(parsed.score).toBe(0.72);
  });

  it("lowercases the coin in the endpoint path", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      mockFetchResponse({ score: 0.5 })
    );
    vi.stubGlobal("fetch", fetcher);

    await callTool("x402_sentiment", { coin: "ETH" });
    expect(fetcher.mock.calls[0][0]).toContain("/test/sentiment/eth");
  });
});

// ─── Tool: x402_market_overview ─────────────────────────────────────────────

describe("x402_market_overview", () => {
  it("returns market overview (free mode)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({ overall_sentiment: 0.6, top_movers: ["BTC", "ETH"] })
      )
    );

    const { parsed } = await callTool("x402_market_overview");
    expect(parsed.mode).toBe("free_test");
    expect(parsed.overall_sentiment).toBe(0.6);
  });
});

// ─── Tool: x402_intelligence ────────────────────────────────────────────────

describe("x402_intelligence", () => {
  it("returns intelligence analysis (free mode)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({
          market: { price: 65000 },
          news: [{ title: "BTC surges" }],
          synthesis: "Bullish momentum",
        })
      )
    );

    const { parsed } = await callTool("x402_intelligence", { coin: "BTC" });
    expect(parsed.mode).toBe("free_test");
    expect(parsed.coin).toBe("BTC");
    expect(parsed.synthesis).toBe("Bullish momentum");
  });

  it("lowercases the coin in the endpoint path", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      mockFetchResponse({ market: {} })
    );
    vi.stubGlobal("fetch", fetcher);

    await callTool("x402_intelligence", { coin: "SOL" });
    expect(fetcher.mock.calls[0][0]).toContain("/test/intelligence/sol");
  });
});

// ─── Tool: x402_send_email ──────────────────────────────────────────────────

describe("x402_send_email", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({ message_id: "test_123" })
      )
    );

    const { parsed } = await callTool("x402_send_email", {
      to: "test@example.com",
      subject: "Hello",
      body: "Test body",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.message_id).toBe("test_123");
  });

  it("uses GET /send/test in free mode (not POST)", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      mockFetchResponse({ message_id: "test_123" })
    );
    vi.stubGlobal("fetch", fetcher);

    await callTool("x402_send_email", {
      to: "a@b.com",
      subject: "Hi",
      body: "Body",
    });

    // Free mode should GET /send/test, not POST /send
    const [url, opts] = fetcher.mock.calls[0];
    expect(url).toContain("/send/test");
    expect(opts).toBeUndefined(); // GET has no options
  });
});

// ─── Tool: x402_scrape_url ──────────────────────────────────────────────────

describe("x402_scrape_url", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({
          markdown: "# Example\nHello world",
          links: ["https://example.com/about"],
        })
      )
    );

    const { parsed } = await callTool("x402_scrape_url", {
      url: "https://example.com",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.markdown).toContain("Example");
  });
});

// ─── Tool: x402_convert_file ────────────────────────────────────────────────

describe("x402_convert_file", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({ output: "base64bytes", mime_type: "image/jpeg" })
      )
    );

    const { parsed } = await callTool("x402_convert_file", {
      url: "https://example.com/img.png",
      type: "image",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.output).toBe("base64bytes");
  });
});

// ─── Tool: x402_web_search ──────────────────────────────────────────────────

describe("x402_web_search", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({
          results: [{ title: "Test", url: "https://test.com", score: 0.95 }],
        })
      )
    );

    const { parsed } = await callTool("x402_web_search", {
      query: "test query",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.results).toHaveLength(1);
  });
});

// ─── Tool: x402_transcribe_audio ────────────────────────────────────────────

describe("x402_transcribe_audio", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({
          transcript: "Hello world",
          language: "en",
          confidence: 0.97,
          duration: 5.2,
        })
      )
    );

    const { parsed } = await callTool("x402_transcribe_audio", {
      url: "https://example.com/audio.mp3",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.transcript).toBe("Hello world");
    expect(parsed.language).toBe("en");
  });
});

// ─── Tool: x402_crawl_site ──────────────────────────────────────────────────

describe("x402_crawl_site", () => {
  it("returns fixture data in free test mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse({
          seed_url: "https://example.com",
          pages_crawled: 3,
          pages_skipped: 0,
          results: [
            { url: "https://example.com", markdown: "# Home" },
            { url: "https://example.com/about", markdown: "# About" },
            { url: "https://example.com/contact", markdown: "# Contact" },
          ],
        })
      )
    );

    const { parsed } = await callTool("x402_crawl_site", {
      url: "https://example.com",
    });

    expect(parsed.mode).toBe("free_test");
    expect(parsed.pages_crawled).toBe(3);
    expect(parsed.results).toHaveLength(3);
  });
});

// ─── Tool listing ───────────────────────────────────────────────────────────

describe("tool listing", () => {
  it("lists all 12 tools", async () => {
    const { tools } = await client.listTools();
    expect(tools).toHaveLength(12);

    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual([
      "x402_convert_file",
      "x402_crawl_site",
      "x402_intelligence",
      "x402_market_overview",
      "x402_network_info",
      "x402_pdf_extract",
      "x402_scrape_url",
      "x402_screenshot",
      "x402_send_email",
      "x402_sentiment",
      "x402_transcribe_audio",
      "x402_web_search",
    ]);
  });
});
