export type Transaction = {
  transaction_id: string;
  customer_id: string;
  recipient_id: string;
  amount: string;
  currency: string;
  timestamp: string;
  channel: string;
  device_id: string;
  status: "RECEIVED" | "EVALUATED";
};

export type WorklistItem = {
  transaction: Transaction;
  evaluation_id: string | null;
  evaluation_created_at: string | null;
  evaluation_status: string | null;
  strategy: string | null;
  score: number | null;
  risk_level: string | null;
  suggested_action: string | null;
  case_id: string | null;
  case_state: string | null;
  experimental: boolean;
  calibrated: false | null;
  production_eligible: false;
};

export type Worklist = { items: WorklistItem[]; next_cursor: string | null };

export type DemoEvidence = {
  version: string;
  transaction_id: string;
  customer_id: string;
  scenario: string;
  synthetic_only: true;
  real_world_verified: false;
  production_eligible: false;
  verdict_provided: false;
  sender_display_name: string;
  counterparty_display_name: string;
  counterparty_type: string;
  payment_purpose: string;
  location: {
    display: string;
    source: string;
    verified_real_world_location: false;
  };
  payment_reference: string;
  support_status: "SUPPORTED" | "PARTIAL" | "UNAVAILABLE";
  artifacts: Array<{ kind: string; reference: string; summary: string }>;
  limitations: string;
};

export type Summary = {
  as_of: string;
  transaction_time_basis: string;
  transactions: number;
  transactions_today: number;
  evaluated_transactions: number;
  high_risk_transactions: number;
  cases_awaiting_review: number;
  confirmed_fraud_cases: number;
  suspicious_amount: string;
  production_model_status: "NO_PRODUCTION_MODEL";
  experimental_results_calibrated: false;
};

export type CaseDocument = {
  case_id: string;
  evaluation_id: string;
  transaction_id: string;
  created_at: string;
  state: string;
  version: number;
  history: Array<{ previous: string; target: string; actor_id: string; timestamp: string }>;
  feedback: Array<{
    feedback_id: string;
    actor_id: string;
    verdict: string;
    timestamp: string;
    comment: string;
    sequence: number;
  }>;
  experimental: true;
  operational_action_executed: false;
  admission_workflow_verified: false;
};

export type EvaluationDocument = {
  evaluation_id: string;
  transaction_id: string;
  customer_id: string;
  currency: string;
  created_at: string;
  production_eligible: false;
  operational_action_executed: false;
  admission_workflow_verified: false;
  risk: {
    status: string;
    score: number | null;
    level: string | null;
    suggested_action: string | null;
    profile_version: number | null;
    unavailable_rules: string[];
    policy: { strategy: string; [key: string]: unknown };
    prediction: { model_version: string; uncalibrated_score: number } | null;
    rules: { outcomes: Array<{
      code: string;
      status: string;
      missing_indicators: string[];
      reason: { code: string; message: string } | null;
    }> };
  };
  sequence_evidence?: {
    sequence_version: string;
    thresholds_calibrated: false;
    outcomes: Array<{
      code: string;
      status: string;
      missing_indicators: string[];
      reason: { code: string; message: string } | null;
    }>;
  };
  explanation: {
    readable: Array<{ code?: string; message?: string; [key: string]: unknown }>;
    model: { readable: Array<{ message: string }>; [key: string]: unknown } | null;
  };
};

export type ProfileDocument = {
  customer_id: string;
  currency: string;
  as_of: string;
  version: number | null;
  status: string;
  timezone: string;
  admission_workflow_verified: boolean;
  admission_policy_version: string | null;
  long_term: ProfileWindow;
  short_term: ProfileWindow;
};

export type ProfileWindow = {
  days: number;
  count: number;
  amounts: { median: string; mad: string; p95: string; mean: string } | null;
  observations_per_day: string;
  typical_local_hours: number[];
  known_recipients: string[];
};
