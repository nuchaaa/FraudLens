import { type FormEvent, useEffect, useMemo, useState } from "react";
import { FraudLensApi } from "./api";
import { Badge, formatMoney, formatTime, riskTone, ShortId, State } from "./components";
import type { CaseDocument, EvaluationDocument, ProfileDocument, Summary, WorklistItem } from "./types";

export function Overview({ api, summary, items, loading, error, openTransactions }: {
  api: FraudLensApi; summary: Summary | null; items: WorklistItem[]; loading: boolean; error: string; openTransactions: () => void;
}) {
  void api;
  if (loading || error || !summary) return <section className="page"><PageHead title="Operational overview" subtitle="Exact scoped counts from retained PostgreSQL records." /><State loading={loading} error={error} /></section>;
  const cards = [
    ["Transactions today", summary.transactions_today, summary.transaction_time_basis],
    ["High-risk evaluations", summary.high_risk_transactions, "Latest retained evaluation per transaction"],
    ["Awaiting review", summary.cases_awaiting_review, "Open or under-review experimental cases"],
    ["Confirmed fraud", summary.confirmed_fraud_cases, "Cases with a retained fraud verdict"],
  ] as const;
  return <section className="page">
    <PageHead title="Operational overview" subtitle={`Scoped snapshot · ${formatTime(summary.as_of)}`} action={<button className="secondary" onClick={openTransactions}>Open worklist →</button>} />
    <div className="notice"><strong>Research mode</strong><span>Scores are experimental, uncalibrated and production-ineligible. Suggested actions are never executed.</span></div>
    <div className="metric-grid">
      {cards.map(([label, value, note]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>)}
    </div>
    <div className="overview-grid">
      <article className="panel"><div className="panel-head"><div><h2>Recent activity</h2><p>Latest visible transactions and retained evaluation state.</p></div></div><MiniTable items={items.slice(0, 5)} /></article>
      <article className="panel posture"><div className="panel-head"><div><h2>Evidence posture</h2><p>What this console can truthfully claim.</p></div></div>
        <div className="posture-row"><span>Production model</span><Badge tone="neutral">Not registered</Badge></div>
        <div className="posture-row"><span>Calibration</span><Badge tone="medium">Not calibrated</Badge></div>
        <div className="posture-row"><span>Operational actions</span><Badge tone="low">Disabled</Badge></div>
        <div className="posture-row"><span>Suspicious amount</span><strong>{formatMoney(summary.suspicious_amount)}</strong></div>
        <p className="fineprint">Suspicious amount sums transactions whose latest retained experimental evaluation is HIGH or CRITICAL.</p>
      </article>
    </div>
  </section>;
}

function MiniTable({ items }: { items: WorklistItem[] }) {
  if (!items.length) return <State empty="Submit synthetic transactions through the authenticated API to populate this view." />;
  return <div className="mini-list">{items.map((item) => <div className="mini-row" key={item.transaction.transaction_id}><div className="transaction-symbol">↗</div><div><strong>{formatMoney(item.transaction.amount, item.transaction.currency)}</strong><span><ShortId value={item.transaction.customer_id} /> · {formatTime(item.transaction.timestamp)}</span></div><Badge tone={riskTone(item.risk_level)}>{evaluationLabel(item)}</Badge></div>)}</div>;
}

export function Transactions({ api, title, items, loading, error, cursor, more, casesOnly, refreshed }: {
  api: FraudLensApi; title: string; items: WorklistItem[]; loading: boolean; error: string; cursor: string | null; more: () => void; casesOnly: boolean; refreshed: () => void;
}) {
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("ALL");
  const [selected, setSelected] = useState<WorklistItem | null>(null);
  const filtered = useMemo(() => items.filter((item) => {
    const matchesText = !query || [item.transaction.transaction_id, item.transaction.customer_id, item.transaction.recipient_id].some((value) => value.toLowerCase().includes(query.toLowerCase()));
    return matchesText && (risk === "ALL" || (risk === "NONE" ? !item.risk_level : item.risk_level === risk));
  }), [items, query, risk]);
  return <section className="page">
    <PageHead title={title} subtitle={casesOnly ? "Experimental cases in the currently loaded scoped worklist." : "Immutable transaction facts joined to their latest retained evaluation."} />
    {!casesOnly && <div className="notice"><strong>Intake is separate from evaluation</strong><span>NOT EVALUATED means no retained assessment exists. It is not a low-risk result. Experimental rules or ML require a separate authorized evaluation; ML also requires a reviewed local bundle.</span></div>}
    <div className="toolbar"><label className="search"><span>⌕</span><input aria-label="Search transactions" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search transaction, customer or recipient" /></label><select aria-label="Filter by risk" value={risk} onChange={(e) => setRisk(e.target.value)}><option value="ALL">All risk states</option><option value="NONE">Not evaluated</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></div>
    <div className="panel table-panel"><State loading={loading} error={error} empty={!loading && !error && !filtered.length ? (casesOnly ? "No cases are visible in this page of the worklist." : "No transactions match these filters.") : undefined} />
      {!!filtered.length && <div className="table-scroll"><table><thead><tr><th>Transaction</th><th>Time</th><th>Customer</th><th>Amount</th><th>Risk</th><th>Decision</th><th>Case</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.transaction.transaction_id} onClick={() => setSelected(item)} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && setSelected(item)}><td><ShortId value={item.transaction.transaction_id} /><small>{item.transaction.channel}</small></td><td>{formatTime(item.transaction.timestamp)}</td><td><ShortId value={item.transaction.customer_id} /></td><td className="amount">{formatMoney(item.transaction.amount, item.transaction.currency)}</td><td><Badge tone={riskTone(item.risk_level)}>{evaluationLabel(item)}</Badge>{item.score != null && <small>{Math.round(item.score * 100)} · uncalibrated</small>}</td><td>{item.suggested_action?.replaceAll("_", " ") ?? "—"}</td><td>{item.case_state ? <Badge tone={item.case_state === "UNDER_REVIEW" ? "medium" : "neutral"}>{item.case_state.replaceAll("_", " ")}</Badge> : "—"}</td></tr>)}</tbody></table></div>}
    </div>
    {cursor && !casesOnly && <button className="load-more" onClick={more}>Load older records</button>}
    {selected && <TransactionDetail api={api} item={selected} close={() => setSelected(null)} refreshed={refreshed} />}
  </section>;
}

function TransactionDetail({ api, item, close, refreshed }: { api: FraudLensApi; item: WorklistItem; close: () => void; refreshed: () => void }) {
  const [evaluation, setEvaluation] = useState<EvaluationDocument | null>(null);
  const [caseDoc, setCaseDoc] = useState<CaseDocument | null>(null);
  const [error, setError] = useState("");
  const [reviewing, setReviewing] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([item.evaluation_id ? api.evaluation(item.evaluation_id) : null, item.case_id ? api.case(item.case_id) : null])
      .then(([nextEvaluation, nextCase]) => { if (active) { setEvaluation(nextEvaluation); setCaseDoc(nextCase); } })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "Detail request failed"));
    return () => { active = false; };
  }, [api, item]);
  return <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && close()}><aside className="drawer" aria-label="Transaction details"><div className="drawer-head"><div><span className="eyebrow">TRANSACTION DETAIL</span><h2>{formatMoney(item.transaction.amount, item.transaction.currency)}</h2><span><ShortId value={item.transaction.transaction_id} /></span></div><button onClick={close} aria-label="Close details">×</button></div>
    {error && <State error={error} />}
    <section className="detail-section"><h3>Transaction facts</h3><div className="fact-grid"><Fact label="Customer"><ShortId value={item.transaction.customer_id} /></Fact><Fact label="Recipient"><ShortId value={item.transaction.recipient_id} /></Fact><Fact label="Occurred">{formatTime(item.transaction.timestamp)}</Fact><Fact label="Channel / device">{item.transaction.channel} · {item.transaction.device_id}</Fact><Fact label="Immutable status"><Badge>{item.transaction.status}</Badge></Fact></div></section>
    <section className="detail-section"><h3>Missing payment context</h3><p className="muted">This intake record has no sender or receiver name, merchant or registered-business identity, purchase purpose, or verified place of payment. Customer and recipient UUIDs are identifiers, not names. A small amount does not establish legitimacy.</p></section>
    <section className="detail-section"><div className="section-title"><h3>Experimental risk</h3><Badge tone={riskTone(item.risk_level)}>{evaluationLabel(item)}</Badge></div>{!item.evaluation_id ? <p className="muted">No retained evaluation exists. The transaction remains RECEIVED.</p> : !evaluation ? <State loading /> : <><div className="risk-hero"><strong>{evaluation.risk.score == null ? "—" : `${Math.round(evaluation.risk.score * 100)}`}</strong><span>{evaluation.risk.score == null ? "Insufficient evidence" : "uncalibrated index / 100"}</span></div><div className="fact-grid"><Fact label="Strategy">{evaluation.risk.policy.strategy}</Fact><Fact label="Suggested action">{evaluation.risk.suggested_action?.replaceAll("_", " ") ?? "None"}</Fact><Fact label="Profile revision">{evaluation.risk.profile_version ?? "Explicitly absent"}</Fact><Fact label="Production eligible"><Badge tone="critical">No</Badge></Fact></div><ReasonList evaluation={evaluation} /></>}</section>
    {caseDoc && <section className="detail-section"><div className="section-title"><h3>Review case</h3><Badge tone={caseDoc.state === "UNDER_REVIEW" ? "medium" : "neutral"}>{caseDoc.state.replaceAll("_", " ")}</Badge></div><p className="muted">Version {caseDoc.version} · {caseDoc.feedback.length} feedback record(s). Feedback does not update the profile.</p><button className="primary compact" onClick={() => setReviewing(true)}>Review case</button></section>}
    {reviewing && caseDoc && <ReviewDialog api={api} value={caseDoc} close={() => setReviewing(false)} saved={(next) => { setCaseDoc(next); setReviewing(false); refreshed(); }} />}
  </aside></div>;
}

function ReasonList({ evaluation }: { evaluation: EvaluationDocument }) {
  const rules = evaluation.risk.rules?.outcomes ?? [];
  const sequence = evaluation.sequence_evidence?.outcomes ?? [];
  const model = evaluation.explanation.model?.readable ?? [];
  const reasons = [
    ...rules.filter((rule) => rule.reason).map((rule) => ({ key: `rule-${rule.code}`, message: rule.reason!.message, status: rule.status })),
    ...sequence.filter((signal) => signal.reason).map((signal) => ({ key: `sequence-${signal.code}`, message: signal.reason!.message, status: signal.status })),
    ...model.map((reason, index) => ({ key: `model-${index}`, message: reason.message, status: "MODEL" })),
  ];
  return <div className="reasons"><h4>Retained reasons</h4>{reasons.length ? reasons.map((reason) => <div className="reason" key={reason.key}><span>{reason.status === "MATCHED" ? "!" : reason.status === "MODEL" ? "↗" : "·"}</span><div><strong>{reason.message}</strong><small>{reason.status.replaceAll("_", " ")}</small></div></div>) : <p className="muted">No matched reason is available. Missing evidence is retained in the evaluation.</p>}</div>;
}

function ReviewDialog({ api, value, close, saved }: { api: FraudLensApi; value: CaseDocument; close: () => void; saved: (value: CaseDocument) => void }) {
  const [verdict, setVerdict] = useState("NEEDS_INVESTIGATION");
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const action = value.state === "OPEN" ? "start_review" : value.state === "UNDER_REVIEW" ? "feedback" : value.state === "LEGITIMATE" || value.state === "CONFIRMED_FRAUD" ? "close" : null;
  async function confirm() {
    if (!action) return;
    setBusy(true); setError("");
    try {
      const body = action === "feedback" ? { expected_version: value.version, action, verdict, comment } : { expected_version: value.version, action };
      saved(await api.review(value.case_id, body));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Review failed"); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="review-title"><span className="eyebrow">CONFIRM IMMUTABLE REVIEW ACTION</span><h2 id="review-title">{action?.replaceAll("_", " ") ?? "Case is closed"}</h2><p>This appends review history. It does not execute the suggested action or authorize profile learning.</p>{action === "feedback" && <><label>Verdict<select value={verdict} onChange={(e) => setVerdict(e.target.value)}><option>NEEDS_INVESTIGATION</option><option>LEGITIMATE</option><option>CONFIRMED_FRAUD</option></select></label><label>Evidence comment<textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} placeholder="Describe the reviewed synthetic evidence" /></label></>}{error && <div className="form-error">{error}</div>}<div className="modal-actions"><button className="secondary" onClick={close}>Cancel</button>{action && <button className="primary" disabled={busy || (action === "feedback" && !comment.trim())} onClick={confirm}>{busy ? "Saving…" : "Confirm append"}</button>}</div></div></div>;
}

export function Customers({ api }: { api: FraudLensApi }) {
  const [customer, setCustomer] = useState(""); const [currency, setCurrency] = useState("KZT"); const [profile, setProfile] = useState<ProfileDocument | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); setProfile(null); try { setProfile(await api.profile(customer.trim(), currency)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Profile request failed"); } finally { setBusy(false); } }
  return <section className="page"><PageHead title="Customer behavior" subtitle="Read a scoped robust profile by synthetic customer ID and currency." /><form className="profile-search panel" onSubmit={submit}><label>Customer UUID<input required value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="00000000-0000-4000-8000-000000000001" /></label><label>Currency<select value={currency} onChange={(e) => setCurrency(e.target.value)}><option>KZT</option><option>USD</option><option>EUR</option></select></label><button className="primary" disabled={busy}>{busy ? "Loading…" : "Read profile"}</button></form>{error && <State error={error} />}{profile && <ProfileView profile={profile} />}</section>;
}

function ProfileView({ profile }: { profile: ProfileDocument }) {
  return <div className="profile-grid"><article className="panel profile-summary"><div className="panel-head"><div><h2>Baseline status</h2><p><ShortId value={profile.customer_id} /> · {profile.currency}</p></div><Badge tone={profile.admission_workflow_verified ? "low" : "medium"}>{profile.admission_workflow_verified ? "VERIFIED WORKFLOW" : "UNVERIFIED / COLD"}</Badge></div><div className="profile-status">{profile.status.replaceAll("_", " ")}</div><p>Revision {profile.version ?? "none"} · {profile.timezone}</p><p className="fineprint">A sufficient history label describes sample size. It is not a legitimacy or fraud verdict.</p></article><Window title="Long-term baseline" value={profile.long_term} /><Window title="Short-term baseline" value={profile.short_term} /></div>;
}

function Window({ title, value }: { title: string; value: ProfileDocument["long_term"] }) {
  return <article className="panel window"><div className="panel-head"><div><h2>{title}</h2><p>{value.days} days · {value.count} admitted observations</p></div></div>{value.amounts ? <div className="stat-list"><Fact label="Median">{formatMoney(value.amounts.median)}</Fact><Fact label="MAD">{formatMoney(value.amounts.mad)}</Fact><Fact label="P95">{formatMoney(value.amounts.p95)}</Fact><Fact label="Mean">{formatMoney(value.amounts.mean)}</Fact></div> : <State empty="No admitted amounts are available in this window." />}<p className="fineprint">Typical local hours: {value.typical_local_hours.length ? value.typical_local_hours.join(", ") : "unavailable"} · Known recipients: {value.known_recipients.length}</p></article>;
}

export function Models({ items }: { items: WorklistItem[] }) {
  const evaluated = items.filter((item) => item.evaluation_id).length;
  return <section className="page"><PageHead title="Models & evidence" subtitle="Deployment status without invented registry metadata." /><div className="notice danger"><strong>No production model</strong><span>The available native XGBoost bundle is synthetic-only, uncalibrated and not loaded unless the experimental backend is explicitly configured.</span></div><div className="metric-grid three"><article className="metric"><span>Production status</span><strong className="text-value">Unavailable</strong><small>No model has production eligibility.</small></article><article className="metric"><span>Loaded-page evaluations</span><strong>{evaluated}</strong><small>Each evaluation retains its own exact provenance.</small></article><article className="metric"><span>Feature contract</span><strong className="text-value">behavior-v1</strong><small>29 ordered finite features.</small></article></div><article className="panel prose"><h2>Why metrics are not shown here</h2><p>The backend has no truthful production model registry record: the legacy synthetic model lacks an exact training timestamp, and the external ULB benchmark is behaviorally incompatible. Recorded retrospective metrics remain in research artifacts rather than being presented as live model health.</p><p>Open a transaction evaluation to inspect its exact model version, policy, rules and explanation.</p></article></section>;
}

export function System({ summary }: { summary: Summary | null }) {
  return <section className="page"><PageHead title="System & audit" subtitle="Current boundaries visible to the analyst console." /><div className="system-grid"><article className="panel"><h2>API connection</h2><div className="posture-row"><span>Authentication</span><Badge tone="low">Scoped credential</Badge></div><div className="posture-row"><span>Cache policy</span><Badge>No store</Badge></div><div className="posture-row"><span>Snapshot</span><span>{summary ? formatTime(summary.as_of) : "Unavailable"}</span></div></article><article className="panel"><h2>Event delivery</h2><div className="posture-row"><span>Destination</span><span>Local recorder</span></div><div className="posture-row"><span>Guarantee</span><Badge tone="medium">At least once</Badge></div><p className="fineprint">Detailed queue/dead-letter status is intentionally restricted to the local database-operator CLI.</p></article><article className="panel"><h2>Audit access</h2><State empty="Immutable audit records exist, but no scoped audit-list HTTP endpoint is exposed yet." /></article></div></section>;
}

function PageHead({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) { return <div className="page-head"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>; }
function Fact({ label, children }: { label: string; children: React.ReactNode }) { return <div className="fact"><span>{label}</span><strong>{children}</strong></div>; }
function evaluationLabel(item: WorklistItem) {
  return item.risk_level ?? item.evaluation_status?.replaceAll("_", " ") ?? "NOT EVALUATED";
}
