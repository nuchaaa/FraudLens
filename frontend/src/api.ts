import type {
  CaseDocument,
  EvaluationDocument,
  ProfileDocument,
  Summary,
  Transaction,
  Worklist,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export class FraudLensApi {
  constructor(private readonly token: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(path, {
      ...init,
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        // A non-JSON reverse-proxy error is represented by its status only.
      }
      throw new ApiError(detail, response.status);
    }
    return (await response.json()) as T;
  }

  summary(): Promise<Summary> {
    return this.request("/api/v1/console/summary");
  }

  worklist(cursor?: string): Promise<Worklist> {
    const query = cursor ? `?limit=50&cursor=${encodeURIComponent(cursor)}` : "?limit=50";
    return this.request(`/api/v1/console/worklist${query}`);
  }

  transaction(id: string): Promise<Transaction> {
    return this.request(`/api/v1/transactions/${encodeURIComponent(id)}`);
  }

  evaluation(id: string): Promise<EvaluationDocument> {
    return this.request(`/api/v1/experimental/evaluations/${encodeURIComponent(id)}`);
  }

  case(id: string): Promise<CaseDocument> {
    return this.request(`/api/v1/experimental/cases/${encodeURIComponent(id)}`);
  }

  profile(customerId: string, currency: string): Promise<ProfileDocument> {
    return this.request(
      `/api/v1/customers/${encodeURIComponent(customerId)}/profiles/${encodeURIComponent(currency)}`,
    );
  }

  review(
    caseId: string,
    body: { expected_version: number; action: string; verdict?: string; comment?: string },
  ): Promise<CaseDocument> {
    return this.request(`/api/v1/experimental/cases/${encodeURIComponent(caseId)}/review`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }
}
