import { afterEach, describe, expect, it, vi } from "vitest";
import { FraudLensApi, loginWithSecurityKey, restoreSession } from "./api";

vi.mock("./webauthn", () => ({
  authenticateCredential: vi.fn(async () => ({ id: "assertion" })),
  registerCredential: vi.fn(async () => ({ id: "registration" })),
}));

const session = {
  account_id: "00000000-0000-4000-8000-000000000001",
  role: "analyst", customer_ids: [], csrf: "next-csrf",
};

afterEach(() => vi.restoreAllMocks());

describe("browser session transport", () => {
  it("issues a human session only after the security-key assertion", async () => {
    const requests: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      requests.push([String(path), init]);
      return new Response(JSON.stringify(requests.length === 1
        ? { challenge_id: "challenge", public_key: { challenge: "opaque" } } : session),
      { status: 200 });
    }));
    expect(await loginWithSecurityKey("analyst", "password")).toEqual(session);
    expect(requests.map(([path]) => path)).toEqual([
      "/api/v1/auth/mfa/login/options", "/api/v1/auth/mfa/login/verify",
    ]);
    expect(JSON.parse(String(requests[1][1]?.body))).toEqual({
      challenge_id: "challenge", credential: { id: "assertion" },
    });
  });

  it("passes CSRF on first-factor enrollment and disconnects after revocation", async () => {
    const expired = vi.fn();
    const requests: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      requests.push([String(path), init]);
      return new Response(JSON.stringify(requests.length === 1
        ? { challenge_id: "challenge", public_key: { challenge: "opaque" } }
        : { enrolled: true }), { status: requests.length === 1 ? 200 : 201 });
    }));
    await new FraudLensApi("csrf", expired).enrollFirstSecurityKey("password");
    expect(requests).toHaveLength(2);
    expect((requests[0][1]?.headers as Record<string, string>)["X-CSRF-Token"]).toBe("csrf");
    expect((requests[1][1]?.headers as Record<string, string>)["X-CSRF-Token"]).toBe("csrf");
    expect(expired).toHaveBeenCalledOnce();
  });

  it("proves an existing key before registering another", async () => {
    const expired = vi.fn();
    const requests: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      requests.push([String(path), init]);
      return new Response(JSON.stringify(requests.length < 3
        ? { challenge_id: `challenge-${requests.length}`, public_key: { challenge: "opaque" } }
        : { enrolled: true }), { status: requests.length === 3 ? 201 : 200 });
    }));
    await new FraudLensApi("csrf", expired).enrollAnotherSecurityKey("password");
    expect(requests.map(([path]) => path)).toEqual([
      "/api/v1/auth/mfa/add-factor/options",
      "/api/v1/auth/mfa/add-factor/proof",
      "/api/v1/auth/mfa/add-factor/verify",
    ]);
    expect(JSON.parse(String(requests[1][1]?.body))).toEqual({
      challenge_id: "challenge-1", credential: { id: "assertion" },
    });
    expect(expired).toHaveBeenCalledOnce();
  });

  it("requests a different-key assertion before removing a factor", async () => {
    const expired = vi.fn();
    const requests: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      requests.push([String(path), init]);
      return new Response(JSON.stringify(requests.length === 1
        ? { challenge_id: "proof", public_key: { challenge: "opaque" } }
        : { removed: true }), { status: 200 });
    }));
    await new FraudLensApi("csrf", expired).removeSecurityKey("password", "target");
    expect(requests.map(([path]) => path)).toEqual([
      "/api/v1/auth/mfa/remove-factor/options",
      "/api/v1/auth/mfa/remove-factor/verify",
    ]);
    expect(JSON.parse(String(requests[0][1]?.body))).toEqual({
      password: "password", credential_id: "target",
    });
    expect(expired).toHaveBeenCalledOnce();
  });

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
