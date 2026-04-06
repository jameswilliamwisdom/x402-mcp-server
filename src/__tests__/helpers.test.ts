import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  textResult,
  errorResult,
  apiGet,
  apiPost,
  checkHealth,
  APIS,
  getPrivateKey,
  resetPaidFetch,
} from "../helpers.js";

// ─── Mock fetch globally ────────────────────────────────────────────────────

function mockFetch(body: unknown, opts: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = opts;
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
  });
}

// ─── textResult / errorResult ───────────────────────────────────────────────

describe("textResult", () => {
  it("wraps a string as text content", () => {
    const r = textResult("hello");
    expect(r.content).toEqual([{ type: "text", text: "hello" }]);
  });

  it("JSON-stringifies objects", () => {
    const r = textResult({ foo: 1 });
    expect(JSON.parse(r.content[0].text)).toEqual({ foo: 1 });
  });

  it("pretty-prints JSON with 2-space indent", () => {
    const r = textResult({ a: 1 });
    expect(r.content[0].text).toBe(JSON.stringify({ a: 1 }, null, 2));
  });
});

describe("errorResult", () => {
  it("returns isError: true with prefixed message", () => {
    const r = errorResult("boom");
    expect(r.isError).toBe(true);
    expect(r.content[0].text).toBe("Error: boom");
  });
});

// ─── apiGet ─────────────────────────────────────────────────────────────────

describe("apiGet", () => {
  beforeEach(() => {
    resetPaidFetch();
    delete process.env.X402_PRIVATE_KEY;
  });

  it("fetches JSON from the given URL", async () => {
    const fetcher = mockFetch({ status: "ok" });
    vi.stubGlobal("fetch", fetcher);

    const data = await apiGet("https://api.example.com", "/health");
    expect(fetcher).toHaveBeenCalledWith("https://api.example.com/health");
    expect(data).toEqual({ status: "ok" });
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetch("Not Found", { ok: false, status: 404 }));

    await expect(apiGet("https://api.example.com", "/bad")).rejects.toThrow(
      "API 404"
    );
  });

  it("includes response body in error message", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch("rate limit exceeded", { ok: false, status: 429 })
    );

    await expect(apiGet("https://api.example.com", "/x")).rejects.toThrow(
      "rate limit exceeded"
    );
  });
});

// ─── apiPost ────────────────────────────────────────────────────────────────

describe("apiPost", () => {
  beforeEach(() => {
    resetPaidFetch();
    delete process.env.X402_PRIVATE_KEY;
  });

  it("sends JSON POST and returns parsed response", async () => {
    const fetcher = mockFetch({ id: "msg_123" });
    vi.stubGlobal("fetch", fetcher);

    const data = await apiPost("https://api.example.com", "/send", {
      to: "a@b.com",
    });

    expect(fetcher).toHaveBeenCalledWith("https://api.example.com/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to: "a@b.com" }),
    });
    expect(data).toEqual({ id: "msg_123" });
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch("server error", { ok: false, status: 500 })
    );

    await expect(
      apiPost("https://api.example.com", "/send", {})
    ).rejects.toThrow("API 500");
  });
});

// ─── checkHealth ────────────────────────────────────────────────────────────

describe("checkHealth", () => {
  it("returns healthy when /health succeeds", async () => {
    vi.stubGlobal("fetch", mockFetch({ uptime: 1234 }));

    const result = await checkHealth("https://api.example.com");
    expect(result.healthy).toBe(true);
    expect(result.details).toEqual({ uptime: 1234 });
  });

  it("falls back to / when /health fails", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ root: true }),
      });
    vi.stubGlobal("fetch", fetcher);

    const result = await checkHealth("https://api.example.com");
    expect(result.healthy).toBe(true);
    expect(result.details).toEqual({ root: true });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("returns unhealthy when both /health and / fail", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", fetcher);

    const result = await checkHealth("https://api.example.com");
    expect(result.healthy).toBe(false);
    expect(result.error).toBe("HTTP 503");
  });

  it("returns unhealthy on network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("ECONNREFUSED"))
    );

    const result = await checkHealth("https://api.example.com");
    expect(result.healthy).toBe(false);
    expect(result.error).toBe("ECONNREFUSED");
  });
});

// ─── APIS constant ──────────────────────────────────────────────────────────

describe("APIS", () => {
  it("has 8 API entries", () => {
    expect(Object.keys(APIS)).toHaveLength(8);
  });

  it("all entries have required fields", () => {
    for (const [key, api] of Object.entries(APIS)) {
      expect(api.name).toBeTruthy();
      expect(api.baseUrl).toMatch(/^https?:\/\//);
      expect(api.price).toBeTruthy();
      expect(api.description).toBeTruthy();
      expect(api.usesX402).toBe(true);
    }
  });
});

// ─── getPrivateKey ──────────────────────────────────────────────────────────

describe("getPrivateKey", () => {
  it("returns undefined when env var is not set", () => {
    delete process.env.X402_PRIVATE_KEY;
    expect(getPrivateKey()).toBeUndefined();
  });

  it("returns the key when set", () => {
    process.env.X402_PRIVATE_KEY = "0xdeadbeef";
    expect(getPrivateKey()).toBe("0xdeadbeef");
    delete process.env.X402_PRIVATE_KEY;
  });
});
