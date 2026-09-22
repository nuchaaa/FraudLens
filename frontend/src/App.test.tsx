import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const summary = {
  as_of: "2026-09-22T10:00:00Z",
  transaction_time_basis: "transaction event timestamps in UTC",
  transactions: 2,
  transactions_today: 1,
  evaluated_transactions: 1,
  high_risk_transactions: 0,
  cases_awaiting_review: 0,
  confirmed_fraud_cases: 0,
  suspicious_amount: "0.00",
  production_model_status: "NO_PRODUCTION_MODEL",
  experimental_results_calibrated: false,
};

afterEach(() => vi.restoreAllMocks());

describe("analyst console", () => {
  it("keeps the credential in memory and renders truthful summary data", async () => {
    vi.spyOn(Storage.prototype, "setItem");
    vi.stubGlobal("fetch", vi.fn(async (request: RequestInfo | URL) => {
      const url = String(request);
      return new Response(JSON.stringify(url.includes("summary") ? summary : { items: [], next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Bearer credential"), { target: { value: "short-lived-token" } });
    fireEvent.click(screen.getByRole("button", { name: "Open analyst console" }));
    await waitFor(() => expect(screen.getByText("Not registered")).toBeInTheDocument());
    expect(screen.getByText("Not calibrated")).toBeInTheDocument();
    expect(localStorage.setItem).not.toHaveBeenCalled();
  });

  it("shows authentication failures without entering the workspace", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "valid bearer credential required" }), { status: 401, headers: { "Content-Type": "application/json" } })));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Bearer credential"), { target: { value: "bad-token" } });
    fireEvent.click(screen.getByRole("button", { name: "Open analyst console" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("valid bearer credential required");
  });
});
