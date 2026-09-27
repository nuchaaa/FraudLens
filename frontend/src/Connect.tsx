import { type FormEvent, useState } from "react";
import { loginSession, loginWithSecurityKey, type HumanSession } from "./api";
import { Mark } from "./components";

export function Connect({ onConnect }: { onConnect: (session: HumanSession) => void }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!login || !password) return setError("Enter your login and password.");
    setBusy(true);
    setError("");
    try {
      onConnect(await loginSession(login, password));
      setPassword("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function securityKey() {
    if (!login || !password) return setError("Enter your login and password.");
    setBusy(true);
    setError("");
    try {
      onConnect(await loginWithSecurityKey(login, password));
      setPassword("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Security-key sign-in failed");
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
        <h2>Sign in to your workspace</h2>
        <p>Use a locally provisioned analyst or admin account.</p>
        <label htmlFor="login">Login</label>
        <input id="login" autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} placeholder="Account name" />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Signing in…" : "Open analyst console"}</button>
        <button className="secondary security-key-button" type="button" disabled={busy} onClick={() => void securityKey()}>Sign in with security key</button>
        <div className="privacy-note"><span aria-hidden="true">◉</span><span>Browser session cookies are HttpOnly; no tokens are saved in browser storage.</span></div>
      </form>
    </main>
  );
}

function BadgeLine() {
  return <div className="badge-line"><span className="live-dot" /> Experimental · production ineligible</div>;
}
