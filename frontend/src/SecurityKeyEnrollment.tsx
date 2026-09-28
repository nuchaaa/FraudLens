import { useEffect, useState } from "react";
import type { FraudLensApi, SecurityKey } from "./api";

export function SecurityKeyEnrollment({ api }: { api: FraudLensApi }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [keys, setKeys] = useState<SecurityKey[]>([]);

  useEffect(() => {
    let active = true;
    api.securityKeys().then((items) => { if (active) setKeys(items); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load keys");
      });
    return () => { active = false; };
  }, [api]);

  async function enroll(another: boolean) {
    if (!password) return;
    setBusy(true);
    setError("");
    try {
      if (another) await api.enrollAnotherSecurityKey(password);
      else await api.enrollFirstSecurityKey(password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Enrollment failed");
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  async function remove(credentialId: string) {
    if (!password) return setError("Enter your current password first.");
    setBusy(true);
    setError("");
    try {
      await api.removeSecurityKey(password, credentialId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Key removal failed");
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  return <form className="panel security-key-enrollment" onSubmit={(event) => { event.preventDefault(); void enroll(false); }}>
    <h2>Security keys</h2>
    <p>Local analyst accounts only. To add another key, confirm your password and prove
      possession of an existing key before registering the new one. Enrollment signs
      you out of every session.</p>
    <label htmlFor="enrollment-password">Current password</label>
    <input id="enrollment-password" type="password" autoComplete="current-password"
      value={password} onChange={(event) => setPassword(event.target.value)} />
    {error && <div className="form-error" role="alert">{error}</div>}
    <button className="primary" disabled={busy || !password}>
      {busy ? "Waiting for security key…" : "Enroll first key"}
    </button>
    <button className="secondary security-key-button" type="button" disabled={busy || !password}
      onClick={() => void enroll(true)}>
      Add another key
    </button>
    <h3>Enrolled keys</h3>
    {keys.length === 0 ? <p>No security keys are enrolled on this account.</p> :
      <ul className="security-key-list">{keys.map((key) => <li key={key.credential_id}>
        <span>Key {key.credential_id.slice(0, 10)}… · added {new Date(key.created_at).toLocaleDateString()}</span>
        <button className="secondary" type="button" disabled={busy || !password || keys.length < 2}
          onClick={() => void remove(key.credential_id)}>Remove using another key</button>
      </li>)}</ul>}
    <p className="fineprint">At least one key must remain. Key changes sign out every session.
      Lost-key recovery is not available in this local research console.</p>
  </form>;
}
