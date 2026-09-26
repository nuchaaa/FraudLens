import { afterEach, describe, expect, it, vi } from "vitest";
import { FraudLensApi, restoreSession } from "./api";

const session = {
  account_id: "00000000-0000-4000-8000-000000000001",
  role: "analyst", customer_ids: [], csrf: "next-csrf",
};

afterEach(() => vi.restoreAllMocks());

describe("browser session transport", () => {
  it("recovers an expired access cookie using the current refresh cookie", async () => {
    const calls: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      calls.push([String(path), init]);
      return new Response(JSON.stringify(calls.length === 1
        ? { refresh_required: true, csrf: "old-csrf" } : session), {
        status: 200, headers: { "Content-Type": "application/json" },
      });
    }));
    expect(await restoreSession()).toEqual(session);
    expect(calls[1][0]).toBe("/api/v1/auth/refresh");
    expect(calls[1][1]?.headers).toEqual({ "X-CSRF-Token": "old-csrf" });
  });

  it("serializes simultaneous refreshes and retries with the new CSRF", async () => {
    let refreshes = 0;
    let ready = false;
    const expired = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path).endsWith("/auth/refresh")) {
        refreshes += 1;
        await Promise.resolve();
        ready = true;
        return new Response(JSON.stringify(session), { status: 200 });
      }
      if (!ready) return new Response("{}", { status: 401 });
      return new Response(JSON.stringify({ ok: true, csrf: (init?.headers as Record<string, string>)["X-CSRF-Token"] }), { status: 200 });
    }));
    const api = new FraudLensApi("old-csrf", expired);
    const [one, two] = await Promise.all([
      api.review("case-1", { expected_version: 1, action: "START_REVIEW" }),
      api.review("case-2", { expected_version: 1, action: "START_REVIEW" }),
    ]);
    expect(refreshes).toBe(1);
    expect((one as unknown as { csrf: string }).csrf).toBe("next-csrf");
    expect((two as unknown as { csrf: string }).csrf).toBe("next-csrf");
    expect(expired).not.toHaveBeenCalled();
  });
});
