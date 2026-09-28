import { useEffect, useState } from "react";
import { FraudLensApi } from "./api";
import { Badge, formatMoney, formatTime, riskTone, ShortId, State } from "./components";
import type { ControlledReport } from "./types";

const scenarios = ["A", "B", "C", "D", "E"] as const;
const titles: Record<(typeof scenarios)[number], string> = {
  A: "Ordinary transfer",
  B: "Exceptional vehicle purchase",
  C: "Transfer after the outlier",
  D: "Gradual behavior change",
  E: "Repeated low-value transfers",
};

function label(value: string): string { return value.replaceAll("_", " "); }

export function ScenarioLab({ api }: { api: FraudLensApi }) {
  const [report, setReport] = useState<ControlledReport | null>(null);
  const [selected, setSelected] = useState<(typeof scenarios)[number]>("A");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api.controlledScenarios()
      .then((value) => { if (active) setReport(value); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Simulator request failed"); });
    return () => { active = false; };
  }, [api]);
  if (!report) return <section className="page"><h1>Controlled scenarios</h1><State loading={!error} error={error} /></section>;
  const checks = Object.entries(report.checks).filter(([key]) => key.startsWith(`${selected}_`));
  const passed = checks.length > 0 && checks.every(([, value]) => value);
  const outcomes = report.outcomes.filter((item) => item.scenario === selected);
  return <section className="page scenario-lab">
    <div className="page-head"><div><h1>Controlled scenarios</h1><p>Five authored stories run against the real pure behavior engines.</p></div><Badge tone="medium">Experimental simulator</Badge></div>
    <div className="notice danger"><strong>Synthetic oracle only</strong><span>These labels and assumed prior approvals are not analyst verdicts, bank evidence, model validation, or stored evaluations. No database writes or banking actions occur.</span></div>
    <div className="metric-grid three">
      <article className="metric"><span>Synthetic customers</span><strong>{report.counts.customers}</strong><small>Independent generated identities</small></article>
      <article className="metric"><span>Prior transactions</span><strong>{report.counts.baseline_transactions.toLocaleString()}</strong><small>200 per customer; 100 assumed admitted in memory</small></article>
      <article className="metric"><span>Scenario transfers</span><strong>{report.counts.scenario_transactions}</strong><small>Rules + sequence + gate; no ML inference</small></article>
    </div>
    <div className="scenario-tabs" role="group" aria-label="Choose scenario">{scenarios.map((key) => {
      const scenarioChecks = Object.entries(report.checks).filter(([name]) => name.startsWith(`${key}_`));
      const okay = scenarioChecks.length > 0 && scenarioChecks.every(([, value]) => value);
      return <button key={key} className={selected === key ? "active" : ""} onClick={() => setSelected(key)} aria-pressed={selected === key}>{key} <Badge tone={okay ? "low" : "critical"}>{okay ? "PASS" : "FAIL"}</Badge></button>;
    })}</div>
    <article className="panel scenario-panel">
      <div className="panel-head"><div><h2>Scenario {selected}: {titles[selected]}</h2><p>{outcomes.length} controlled transfer{outcomes.length === 1 ? "" : "s"}</p></div><Badge tone={passed ? "low" : "critical"}>{passed ? "EXPECTATIONS MET" : "EXPECTATION FAILED"}</Badge></div>
      {selected === "E" && <div className="notice danger"><strong>Detection starts at transfer 3</strong><span>The first two synthetic low-value transfers remain LOW/ALLOW under both policies. risk-v1 stays LOW/ALLOW throughout; risk-v2 raises a review suggestion only after a complete sequence signal matches.</span></div>}
      <div className="scenario-compare"><div><h3>Authored expectations</h3>{Object.entries(report.authored_expectations[selected]).map(([key, value]) => <p key={key}><span>{label(key)}</span><strong>{label(value)}</strong></p>)}</div><div><h3>Observed checks</h3>{checks.map(([key, value]) => <p key={key}><span>{label(key.slice(2))}</span><Badge tone={value ? "low" : "critical"}>{value ? "PASS" : "FAIL"}</Badge></p>)}</div></div>
      <div className="table-scroll"><table><thead><tr><th>Transfer</th><th>Time / purpose</th><th>Authored label</th><th>risk-v1</th><th>risk-v2</th><th>Gate</th><th>Reasons</th></tr></thead><tbody>{outcomes.map((item) => <tr key={item.transaction_id}><td><strong>{formatMoney(item.amount, item.currency)}</strong><small><ShortId value={item.transaction_id} /></small></td><td>{formatTime(item.timestamp)}<small>{item.purpose}</small></td><td>{label(item.authored_label)}</td><td><Badge tone={riskTone(item.risk_level)}>{item.risk_level ?? label(item.risk_status)}</Badge><small>{label(item.suggested_action ?? "none")}</small></td><td><Badge tone={riskTone(item.risk_v2_level)}>{item.risk_v2_level ?? label(item.risk_v2_status)}</Badge><small>{label(item.risk_v2_action ?? "none")}</small></td><td>{label(item.gate_action)}<small>Long median {formatMoney(item.median_before)} → {formatMoney(item.median_after)}</small>{item.short_median_after && <small>Short median {item.short_median_before ? formatMoney(item.short_median_before) : "unavailable"} → {formatMoney(item.short_median_after)}</small>}</td><td>{[...item.rule_reasons, ...item.sequence_reasons].length ? <ul>{[...item.rule_reasons, ...item.sequence_reasons].map((reason, index) => <li key={`${item.transaction_id}-${index}`}>{reason}</li>)}</ul> : <span className="muted">No matched signal</span>}</td></tr>)}</tbody></table></div>
    </article>
    <p className="fineprint">{report.risk_policy}. {report.limitations} Version {report.version}; transaction fixture {report.transaction_fixture_version}.</p>
  </section>;
}
