import type {
  CaseDocument,
  EvaluationDocument,
  ProfileDocument,
  Summary,
  Transaction,
  Worklist,
} from "./types";
import { authenticateCredential, registerCredential } from "./webauthn";

export type HumanSession = {
  account_id: string;
  role: "analyst" | "admin";
  customer_ids: string[];
  csrf: string;
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function checked<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Reverse-proxy failures may not contain JSON.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

async function renew(csrf: string): Promise<HumanSession> {
  return checked<HumanSession>(await fetch("/api/v1/auth/refresh", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: { "X-CSRF-Token": csrf },
  }));
}

export async function restoreSession(): Promise<HumanSession | null> {
  const response = await fetch("/api/v1/auth/session", {
    credentials: "same-origin", cache: "no-store",
  });
  if (response.status === 401 || response.status === 503) return null;
  const value = await checked<HumanSession | { refresh_required: true; csrf: string }>(response);
  if ("refresh_required" in value) {
    try { return await renew(value.csrf); } catch { return null; }
  }
  return value;
}

export async function loginSession(login: string, password: string): Promise<HumanSession> {
  return checked<HumanSession>(await fetch("/api/v1/auth/login", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  }));
}

type Ceremony = { challenge_id: string; public_key: Record<string, unknown> };
export type SecurityKey = {
  credential_id: string; created_at: string; last_used_at: string | null;
  device_type: string; backed_up: boolean;
};

export async function loginWithSecurityKey(login: string, password: string): Promise<HumanSession> {
  const ceremony = await checked<Ceremony>(await fetch("/api/v1/auth/mfa/login/options", {
    method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  }));
  const credential = await authenticateCredential(ceremony);
  return checked<HumanSession>(await fetch("/api/v1/auth/mfa/login/verify", {
    method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id: ceremony.challenge_id, credential }),
  }));
}

export class FraudLensApi {
  private refreshing: Promise<void> | null = null;

  constructor(private csrf: string, private readonly expired: () => void) {}

  private async request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    const unsafe = init.method && !["GET", "HEAD"].includes(init.method.toUpperCase());
    const response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(unsafe ? { "X-CSRF-Token": this.csrf } : {}),
        ...init.headers,
      },
    });
    if (response.status === 401 && retry) {
      try {
        if (!this.refreshing) {
          this.refreshing = renew(this.csrf).then((session) => { this.csrf = session.csrf; });
        }
        await this.refreshing;
        this.refreshing = null;
        return this.request<T>(path, init, false);
      } catch {
        this.refreshing = null;
        this.expired();
      }
    }
    if (response.status === 401) this.expired();
    return checked<T>(response);
  }

  async logout(): Promise<void> {
    try {
      await checked<{ logged_out: boolean }>(await fetch("/api/v1/auth/logout", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "X-CSRF-Token": this.csrf },
      }));
    } finally {
      this.expired();
    }
  }

  async enrollFirstSecurityKey(password: string): Promise<void> {
    const ceremony = await this.request<Ceremony>("/api/v1/auth/mfa/first-factor/options", {
      method: "POST", body: JSON.stringify({ password }),
    });
    const credential = await registerCredential(ceremony);
    await this.request<{ enrolled: boolean }>("/api/v1/auth/mfa/first-factor/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_id: ceremony.challenge_id, credential }),
    }, false);
    this.expired();
  }

  async enrollAnotherSecurityKey(password: string): Promise<void> {
    const proof = await this.request<Ceremony>("/api/v1/auth/mfa/add-factor/options", {
      method: "POST", body: JSON.stringify({ password }),
    });
    const assertion = await authenticateCredential(proof);
    const registration = await this.request<Ceremony>("/api/v1/auth/mfa/add-factor/proof", {
      method: "POST",
      body: JSON.stringify({ challenge_id: proof.challenge_id, credential: assertion }),
    });
    const credential = await registerCredential(registration);
    await this.request<{ enrolled: boolean }>("/api/v1/auth/mfa/add-factor/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_id: registration.challenge_id, credential }),
    }, false);
    this.expired();
  }

  async securityKeys(): Promise<SecurityKey[]> {
    const result = await this.request<{ items: SecurityKey[] }>("/api/v1/auth/mfa/factors");
    return result.items;
  }

  async removeSecurityKey(password: string, credentialId: string): Promise<void> {
    const proof = await this.request<Ceremony>("/api/v1/auth/mfa/remove-factor/options", {
      method: "POST", body: JSON.stringify({ password, credential_id: credentialId }),
    });
    const assertion = await authenticateCredential(proof);
    await this.request<{ removed: boolean }>("/api/v1/auth/mfa/remove-factor/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_id: proof.challenge_id, credential: assertion }),
    }, false);
    this.expired();
  }

  summary(): Promise<Summary> { return this.request("/api/v1/console/summary"); }

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

  evaluateRules(transactionId: string, profileVersion: number | null, idempotencyKey: string): Promise<EvaluationDocument> {
    return this.request("/api/v1/experimental/evaluations", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        transaction_id: transactionId,
        profile_version: profileVersion,
        strategy: "rules_only",
        manifest_sha256: null,
      }),
    });
  }

  case(id: string): Promise<CaseDocument> {
    return this.request(`/api/v1/experimental/cases/${encodeURIComponent(id)}`);
  }

  openCase(evaluationId: string, idempotencyKey: string): Promise<CaseDocument> {
    return this.request("/api/v1/experimental/cases", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ evaluation_id: evaluationId }),
    });
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
