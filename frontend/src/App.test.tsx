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

function mockApi(items: unknown[] = []) {
  vi.stubGlobal("fetch", vi.fn(async (request: RequestInfo | URL) => {
    const url = String(request);
    if (url.endsWith("/auth/session")) return new Response("{}", { status: 401 });
    const body = url.endsWith("/auth/login") ? session : url.includes("summary")
      ? summary : { items, next_cursor: null };
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
}

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
});
