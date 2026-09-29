import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createAnalysis, getSummary, resourceUrl } from "../api/client";

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("posts the file to the versioned endpoint on the configured base URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ analysis_id: "x" }) });
    vi.stubGlobal("fetch", fetchMock);
    await createAnalysis(new File(["a"], "a.csv"));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/analyses");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("maps backend error bodies to ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 404, json: async () => ({ error: { code: "analysis_not_found", message: "Analysis not found." } }),
    }));
    await expect(getSummary("nope")).rejects.toMatchObject({ code: "analysis_not_found", message: "Analysis not found.", status: 404 });
  });

  it("maps network failures and non-JSON errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(getSummary("a")).rejects.toMatchObject({ code: "network_error" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => { throw new Error("html"); } }));
    const error = await getSummary("a").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(502);
  });

  it("builds absolute resource URLs", () => {
    expect(resourceUrl("/api/v1/x")).toBe("http://localhost:8000/api/v1/x");
  });
});
