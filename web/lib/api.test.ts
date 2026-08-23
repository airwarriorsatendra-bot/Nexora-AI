import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./api";

describe("apiRequest", () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

  it("returns a typed successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 })));
    await expect(apiRequest<{ status: string }>("/api/v1/health")).resolves.toEqual({ status: "ok" });
  });

  it("normalizes API error envelopes", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "not_ready", message: "Unavailable", request_id: "request-1" } }), { status: 503 })));
    await expect(apiRequest("/api/v1/ready")).rejects.toMatchObject({
      status: 503,
      code: "not_ready",
      requestId: "request-1",
    });
  });
});
