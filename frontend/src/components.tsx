import type { ReactNode } from "react";

export function Mark() {
  return (
    <span className="mark" aria-hidden="true">
      <svg viewBox="0 0 42 42"><path d="M21 3 36 9v11c0 9.2-5.8 15.3-15 19C11.8 35.3 6 29.2 6 20V9l15-6Z" /><path d="m13 22 5 5 11-12" /></svg>
    </span>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function State({ loading, error, empty }: { loading?: boolean; error?: string; empty?: string }) {
  if (loading) return <div className="state"><span className="spinner" /> Loading retained records…</div>;
  if (error) return <div className="state state-error"><strong>Couldn’t load data</strong><span>{error}</span></div>;
  if (empty) return <div className="state"><strong>No records found</strong><span>{empty}</span></div>;
  return null;
}

export function ShortId({ value }: { value: string }) {
  return <span className="mono" title={value}>{value.slice(0, 8)}…{value.slice(-4)}</span>;
}

export function formatMoney(value: string, currency = "KZT") {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 2 }).format(amount)
    : `${value} ${currency}`;
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function riskTone(level: string | null) {
  if (level === "CRITICAL") return "critical";
  if (level === "HIGH") return "high";
  if (level === "MEDIUM") return "medium";
  if (level === "LOW") return "low";
  return "neutral";
}
