import type { IncidentDetail, IncidentStatus, IncidentSummary } from '../types';

type RcaPayload = {
  root_cause_category: string;
  root_cause_summary: string;
  fix_description: string;
  prevention_plan: string;
  occurred_at: string;
  detected_at: string;
};

const now = Date.now();

function minutesAgo(minutes: number): string {
  return new Date(now - minutes * 60_000).toISOString();
}

function createMockDetail(summary: IncidentSummary): IncidentDetail {
  return {
    ...summary,
    raw_signals: [
      {
        signal_id: `sig-${summary.id}-1`,
        component_id: summary.component_id,
        severity: summary.severity,
        source: 'prometheus',
        summary: `${summary.component_id} threshold breach`,
        payload: { value: Math.round(Math.random() * 1000), unit: 'ms' },
        occurred_at: summary.opened_at,
        ingested_at: summary.opened_at,
        incident_id: summary.id,
      },
    ],
    rca: null,
    state_transitions: [
      {
        id: 1,
        incident_id: summary.id,
        new_status: 'OPEN',
        transitioned_at: summary.opened_at,
        triggered_by: 'monitoring-service',
        notes: 'Incident created from correlated alerts',
      },
    ],
  };
}

const seed: IncidentSummary[] = [
  {
    id: 'INC-1001',
    component_id: 'payments-api',
    severity: 'P0',
    status: 'OPEN',
    title: 'Payment authorization failures > 35%',
    opened_at: minutesAgo(18),
    created_at: minutesAgo(18),
    updated_at: minutesAgo(2),
    signal_count: 26,
    mttr_seconds: null,
    root_cause_category: null,
  },
  {
    id: 'INC-1002',
    component_id: 'checkout-web',
    severity: 'P1',
    status: 'INVESTIGATING',
    title: 'Checkout latency spike in EU region',
    opened_at: minutesAgo(54),
    created_at: minutesAgo(54),
    updated_at: minutesAgo(7),
    signal_count: 14,
    mttr_seconds: null,
    root_cause_category: null,
  },
  {
    id: 'INC-1003',
    component_id: 'inventory-service',
    severity: 'P2',
    status: 'RESOLVED',
    title: 'Stale stock cache on edge nodes',
    opened_at: minutesAgo(130),
    created_at: minutesAgo(130),
    updated_at: minutesAgo(25),
    resolved_at: minutesAgo(28),
    signal_count: 9,
    mttr_seconds: 6120,
    root_cause_category: 'Cache',
  },
  {
    id: 'INC-1004',
    component_id: 'identity-provider',
    severity: 'P0',
    status: 'INVESTIGATING',
    title: 'Token refresh endpoint intermittent 500s',
    opened_at: minutesAgo(36),
    created_at: minutesAgo(36),
    updated_at: minutesAgo(4),
    signal_count: 21,
    mttr_seconds: null,
    root_cause_category: null,
  },
  {
    id: 'INC-1005',
    component_id: 'notification-worker',
    severity: 'P2',
    status: 'CLOSED',
    title: 'Email dispatch backlog after deploy',
    opened_at: minutesAgo(420),
    created_at: minutesAgo(420),
    updated_at: minutesAgo(280),
    resolved_at: minutesAgo(350),
    closed_at: minutesAgo(280),
    signal_count: 6,
    mttr_seconds: 8400,
    root_cause_category: 'Deployment',
  },
  {
    id: 'INC-1006',
    component_id: 'orders-db',
    severity: 'P1',
    status: 'OPEN',
    title: 'Replica lag exceeded SLA for 12m',
    opened_at: minutesAgo(11),
    created_at: minutesAgo(11),
    updated_at: minutesAgo(3),
    signal_count: 11,
    mttr_seconds: null,
    root_cause_category: null,
  },
];

const details = new Map<string, IncidentDetail>(seed.map(item => [item.id, createMockDetail(item)]));
let timelineId = 2;

function sortBySeverity(incidents: IncidentSummary[]): IncidentSummary[] {
  const severityRank = { P0: 0, P1: 1, P2: 2 } as const;
  return [...incidents].sort(
    (left, right) =>
      severityRank[left.severity] - severityRank[right.severity] ||
      +new Date(right.updated_at) - +new Date(left.updated_at),
  );
}

function updateStatusInternal(id: string, targetStatus: IncidentStatus, notes?: string): IncidentSummary {
  const current = details.get(id);
  if (!current) {
    throw new Error('Incident not found');
  }

  const changedAt = new Date().toISOString();
  current.status = targetStatus;
  current.updated_at = changedAt;

  if (targetStatus === 'RESOLVED' || targetStatus === 'CLOSED') {
    current.resolved_at = current.resolved_at ?? changedAt;
  }
  if (targetStatus === 'CLOSED') {
    current.closed_at = changedAt;
  }

  current.state_transitions = [
    ...(current.state_transitions ?? []),
    {
      id: timelineId++,
      incident_id: id,
      new_status: targetStatus,
      transitioned_at: changedAt,
      triggered_by: 'analyst@local',
      notes: notes ?? null,
    },
  ];

  details.set(id, current);
  return { ...current };
}

export const mockApi = {
  listIncidents(limit = 100): IncidentSummary[] {
    return sortBySeverity(Array.from(details.values()).map(incident => ({ ...incident }))).slice(0, limit);
  },
  getIncident(id: string): IncidentDetail {
    const incident = details.get(id);
    if (!incident) {
      throw new Error('Incident not found');
    }
    return JSON.parse(JSON.stringify(incident)) as IncidentDetail;
  },
  updateStatus(id: string, targetStatus: IncidentStatus, notes?: string): IncidentSummary {
    return updateStatusInternal(id, targetStatus, notes);
  },
  createRca(id: string, payload: RcaPayload): IncidentSummary {
    const incident = details.get(id);
    if (!incident) {
      throw new Error('Incident not found');
    }
    incident.rca = payload;
    incident.root_cause_category = payload.root_cause_category;
    incident.updated_at = new Date().toISOString();
    details.set(id, incident);
    return { ...incident };
  },
  closeIncident(id: string): IncidentSummary {
    return updateStatusInternal(id, 'CLOSED', 'RCA submitted and incident closed');
  },
};
