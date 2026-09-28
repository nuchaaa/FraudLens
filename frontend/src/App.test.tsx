import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const session = {
  account_id: "00000000-0000-4000-8000-000000000001",
  role: "analyst", customer_ids: [], csrf: "csrf-value",
};
const summary = {
  as_of: "2026-09-22T10:00:00Z",
  transaction_time_basis: "transaction event timestamps in UTC",
  transactions: 2, transactions_today: 1, evaluated_transactions: 1,
  high_risk_transactions: 0, cases_awaiting_review: 0, confirmed_fraud_cases: 0,
  suspicious_amount: "0.00", production_model_status: "NO_PRODUCTION_MODEL",
  experimental_results_calibrated: false,
};

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function mockApi(items: unknown[] = [], role: "analyst" | "admin" = "analyst") {
  vi.stubGlobal("fetch", vi.fn(async (request: RequestInfo | URL) => {
    const url = String(request);
    if (url.endsWith("/auth/session")) return new Response("{}", { status: 401 });
    const body = url.endsWith("/auth/login") ? { ...session, role } : url.includes("summary")
      ? summary : { items, next_cursor: null };
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
}

const unevaluatedItem = {
  transaction: {
    transaction_id: "00000000-0000-4000-8000-000000000020",
    customer_id: "00000000-0000-4000-8000-000000000021",
    recipient_id: "00000000-0000-4000-8000-000000000022",
    amount: "25000.00", currency: "KZT", timestamp: "2026-09-22T10:00:00Z",
    channel: "MOBILE", device_id: "synthetic", status: "RECEIVED",
  },
  evaluation_id: null, evaluation_created_at: null, evaluation_status: null,
  strategy: null, score: null, risk_level: null, suggested_action: null,
  case_id: null, case_state: null,
};

async function signIn() {
  fireEvent.change(await screen.findByLabelText("Login"), { target: { value: "analyst-one" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long password" } });
  fireEvent.click(screen.getByRole("button", { name: "Open analyst console" }));
}

describe("analyst console", () => {
  it("uses a human session without browser token storage", async () => {
    vi.spyOn(Storage.prototype, "setItem");
    mockApi();
    render(<App />);
    await signIn();
    await waitFor(() => expect(screen.getByText("Not registered")).toBeInTheDocument());
    expect(screen.getByText("Not calibrated")).toBeInTheDocument();
    expect(localStorage.setItem).not.toHaveBeenCalled();
  });

  it("shows authentication failures without entering the workspace", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "invalid credentials" }), {
      status: 401, headers: { "Content-Type": "application/json" },
    })));
    render(<App />);
    await signIn();
    expect(await screen.findByRole("alert")).toHaveTextContent("invalid credentials");
  });

  it("distinguishes retained insufficient evidence from no evaluation", async () => {
    const item = {
      transaction: {
        transaction_id: "00000000-0000-4000-8000-000000000010",
        customer_id: "00000000-0000-4000-8000-000000000011",
        recipient_id: "00000000-0000-4000-8000-000000000012",
        amount: "25000.00", currency: "KZT", timestamp: "2026-09-22T10:00:00Z",
        channel: "MOBILE", device_id: "synthetic", status: "RECEIVED",
      },
      evaluation_id: "00000000-0000-4000-8000-000000000013",
      evaluation_created_at: "2026-09-22T10:01:00Z",
      evaluation_status: "INSUFFICIENT_EVIDENCE",
      strategy: "rules_only", score: null, risk_level: null, suggested_action: null,
      case_id: null, case_state: null,
    };
    mockApi([item]);
    render(<App />);
    await signIn();
    expect(await screen.findByText("INSUFFICIENT EVIDENCE")).toBeInTheDocument();
    expect(screen.queryByText("NOT EVALUATED")).not.toBeInTheDocument();
  });

  it("lets a local admin explicitly capture a rules-only evaluation", async () => {
    const evaluated = {
      evaluation_id: "00000000-0000-4000-8000-000000000023",
      transaction_id: unevaluatedItem.transaction.transaction_id,
      risk: {
        status: "INSUFFICIENT_EVIDENCE", score: null, level: null,
        suggested_action: null, profile_version: null, unavailable_rules: [],
        policy: { strategy: "rules_only" }, prediction: null, rules: { outcomes: [] },
      },
      explanation: { readable: [], model: null },
    };
    const opened = {
      case_id: "00000000-0000-4000-8000-000000000024",
      evaluation_id: evaluated.evaluation_id,
      transaction_id: unevaluatedItem.transaction.transaction_id,
      state: "OPEN", version: 0, feedback: [], history: [],
    };
    const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
      const url = String(request);
      if (url.endsWith("/auth/session")) return new Response("{}", { status: 401 });
      const body = url.endsWith("/auth/login") ? { ...session, role: "admin" }
        : url.endsWith("/api/v1/experimental/evaluations") && init?.method === "POST" ? evaluated
          : url.endsWith("/api/v1/experimental/cases") && init?.method === "POST" ? opened
          : url.includes("summary") ? summary : { items: [unevaluatedItem], next_cursor: null };
      return new Response(JSON.stringify(body), {
        status: body === evaluated || body === opened ? 201 : 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await signIn();
    fireEvent.click(await screen.findByRole("button", { name: "Transactions" }));
    fireEvent.click(await screen.findByRole("row", { name: /25,000/ }));
    expect(screen.getByRole("button", { name: "Run rules-only evaluation" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Profile evidence"), { target: { value: "absent" } });
    fireEvent.click(screen.getByRole("button", { name: "Run rules-only evaluation" }));
    await waitFor(() => expect(screen.getByText("INSUFFICIENT EVIDENCE")).toBeInTheDocument());
    const call = fetchMock.mock.calls.find(([url, init]) =>
      String(url).endsWith("/api/v1/experimental/evaluations") && init?.method === "POST");
    expect(call).toBeDefined();
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      transaction_id: unevaluatedItem.transaction.transaction_id,
      profile_version: null,
      strategy: "rules_only",
      manifest_sha256: null,
    });
    expect(call?.[1]?.headers).toMatchObject({ "X-CSRF-Token": "csrf-value" });
    expect(call?.[1]?.headers).toHaveProperty("Idempotency-Key");
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/api/v1/experimental/cases"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Open review case" }));
    await waitFor(() => expect(screen.getByText(/Version 0 · 0 feedback record/)).toBeInTheDocument());
    const caseCall = fetchMock.mock.calls.find(([url, init]) =>
      String(url).endsWith("/api/v1/experimental/cases") && init?.method === "POST");
    expect(JSON.parse(String(caseCall?.[1]?.body))).toEqual({ evaluation_id: evaluated.evaluation_id });
  });

  it("does not offer evaluation writes to analysts", async () => {
    mockApi([unevaluatedItem]);
    render(<App />);
    await signIn();
    fireEvent.click(await screen.findByRole("button", { name: "Transactions" }));
    fireEvent.click(await screen.findByRole("row", { name: /25,000/ }));
    expect(screen.queryByRole("button", { name: "Run rules-only evaluation" })).not.toBeInTheDocument();
  });
});
