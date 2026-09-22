import { type FormEvent, useState } from "react";
import { FraudLensApi } from "./api";
import { Mark } from "./components";

export function Connect({ onConnect }: { onConnect: (token: string) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const candidate = token.trim();
    if (!candidate) return setError("Enter a short-lived local API credential.");
    setBusy(true);
    setError("");
    try {
      await new FraudLensApi(candidate).summary();
      onConnect(candidate);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="connect-page">
      <section className="connect-copy">
        <div className="brand"><Mark /><span>FraudLens</span></div>
        <BadgeLine />
        <h1>Behavioral fraud review, with the evidence left intact.</h1>
        <p>Inspect synthetic transactions, experimental evaluations and safe profile history from the local FraudLens API.</p>
        <div className="trust-grid">
          <div><strong>Explainable</strong><span>Rules and model contributions retain their original context.</span></div>
          <div><strong>Scoped</strong><span>The API controls which synthetic customers this credential can see.</span></div>
          <div><strong>Conservative</strong><span>Analyst feedback and profile learning remain separate decisions.</span></div>
        </div>
      </section>
      <form className="connect-card" onSubmit={submit}>
        <div className="eyebrow">LOCAL RESEARCH CONSOLE</div>
        <h2>Connect to your workspace</h2>
        <p>Use an expiring analyst or admin service credential from <code>development.md</code>.</p>
        <label htmlFor="token">Bearer credential</label>
        <input id="token" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste token" />
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Checking…" : "Open analyst console"}</button>
        <div className="privacy-note"><span aria-hidden="true">◉</span><span>Held only in this tab’s memory. Refreshing clears it.</span></div>
      </form>
    </main>
  );
}

function BadgeLine() {
  return <div className="badge-line"><span className="live-dot" /> Experimental · production ineligible</div>;
}
