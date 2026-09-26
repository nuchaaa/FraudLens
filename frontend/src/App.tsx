import { useEffect, useMemo, useState } from "react";
import { FraudLensApi, restoreSession, type HumanSession } from "./api";
import { Mark } from "./components";
import { Connect } from "./Connect";
import { Customers, Models, Overview, System, Transactions } from "./pages";
import type { Summary, WorklistItem } from "./types";

export type Page = "overview" | "transactions" | "cases" | "customers" | "models" | "system";

const navigation: Array<[Page, string, string]> = [
  ["overview", "Overview", "⌂"],
  ["transactions", "Transactions", "↔"],
  ["cases", "Fraud cases", "◇"],
  ["customers", "Customers", "◎"],
  ["models", "Models", "⌁"],
  ["system", "System", "⚙"],
];

export function App() {
  const [session, setSession] = useState<HumanSession | null>(null);
  const [booting, setBooting] = useState(true);
  useEffect(() => {
    let active = true;
    restoreSession().then((value) => { if (active) setSession(value); })
      .catch(() => { if (active) setSession(null); })
      .finally(() => { if (active) setBooting(false); });
    return () => { active = false; };
  }, []);
  if (booting) return <main className="connect-page"><p>Checking session…</p></main>;
  if (!session) return <Connect onConnect={setSession} />;
  return <Console session={session} disconnect={() => setSession(null)} />;
}

function Console({ session, disconnect }: { session: HumanSession; disconnect: () => void }) {
  const api = useMemo(() => new FraudLensApi(session.csrf, disconnect), [session.csrf, disconnect]);
  const [page, setPage] = useState<Page>("overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [items, setItems] = useState<WorklistItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([api.summary(), api.worklist()])
      .then(([nextSummary, worklist]) => {
        if (!active) return;
        setSummary(nextSummary);
        setItems(worklist.items);
        setCursor(worklist.next_cursor);
      })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "Request failed"))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [api, refreshKey]);

  function refresh() {
    setLoading(true);
    setError("");
    setRefreshKey((value) => value + 1);
  }

  async function more() {
    if (!cursor) return;
    try {
      const worklist = await api.worklist(cursor);
      setItems((current) => [...current, ...worklist.items]);
      setCursor(worklist.next_cursor);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Request failed");
    }
  }

  const shownItems = page === "cases" ? items.filter((item) => item.case_id) : items;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Mark /><span>FraudLens</span></div>
        <div className="workspace-label">ANALYST WORKSPACE</div>
        <nav aria-label="Primary navigation">
          {navigation.map(([key, label, icon]) => (
            <button key={key} className={page === key ? "active" : ""} onClick={() => setPage(key)}>
              <span aria-hidden="true">{icon}</span>{label}
              {key === "cases" && summary && summary.cases_awaiting_review > 0 && <em>{summary.cases_awaiting_review}</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="scope-card"><span className="live-dot" /><div><strong>{session.role}</strong><small>Scoped human session</small></div></div>
          <button className="disconnect" onClick={() => void api.logout()}>Sign out</button>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div><span className="crumb">Fraud operations /</span> {navigation.find(([key]) => key === page)?.[1]}</div>
          <div className="top-actions"><span className="experimental-pill">Experimental data</span><button onClick={refresh} aria-label="Refresh data">↻</button></div>
        </header>
        {page === "overview" && <Overview api={api} summary={summary} items={items} loading={loading} error={error} openTransactions={() => setPage("transactions")} />}
        {(page === "transactions" || page === "cases") && <Transactions api={api} title={page === "cases" ? "Fraud cases" : "Transaction worklist"} items={shownItems} loading={loading} error={error} cursor={cursor} more={more} casesOnly={page === "cases"} refreshed={() => setRefreshKey((v) => v + 1)} />}
        {page === "customers" && <Customers api={api} />}
        {page === "models" && <Models items={items} />}
        {page === "system" && <System summary={summary} />}
      </main>
    </div>
  );
}
