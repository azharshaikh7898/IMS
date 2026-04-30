export type Severity = 'P0' | 'P1' | 'P2';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';

export type IncidentSummary = {
  id: string;
  component_id: string;
  severity: Severity;
  status: IncidentStatus;
  title: string;
  opened_at: string;
  created_at?: string;
  resolved_at?: string | null;
  closed_at?: string | null;
  mttr_seconds?: number | null;
  signal_count: number;
  root_cause_category?: string | null;
  updated_at: string;
};

export type RawSignal = {
  signal_id: string;
  component_id: string;
  severity: Severity;
  source: string;
  summary: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  ingested_at: string;
  incident_id?: string;
};

export type StateTransitionEvent = {
  id: number;
  incident_id: string;
  new_status: IncidentStatus;
  transitioned_at: string;
  triggered_by: string;
  notes?: string | null;
};

export type IncidentDetail = IncidentSummary & {
  raw_signals: RawSignal[];
  rca?: {
    root_cause_category: string;
    root_cause_summary: string;
    fix_description: string;
    prevention_plan: string;
    occurred_at: string;
    detected_at: string;
  } | null;
  state_transitions?: StateTransitionEvent[];
};
