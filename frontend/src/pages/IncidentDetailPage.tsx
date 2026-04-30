import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { RcaForm } from '../components/RcaForm';
import { SeverityBadge } from '../components/SeverityBadge';
import { Skeleton } from '../components/Skeleton';
import type { IncidentDetail, StateTransitionEvent } from '../types';

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatTime(value?: string | null): string {
  if (!value) return 'Not yet';
  return timeFormatter.format(new Date(value));
}

function buildTimelineFromTransitions(incident: IncidentDetail): Array<{ label: string; at: string; active: boolean }> {
  // If we have real state transitions from the audit log, use them
  if (incident.state_transitions && incident.state_transitions.length > 0) {
    return incident.state_transitions.map(transition => ({
      label: transition.new_status,
      at: transition.transitioned_at,
      active: true
    }));
  }

  // Fallback to derived timeline (for backward compatibility)
  return [
    { label: 'Opened', at: incident.opened_at, active: true },
    { label: 'Investigating', at: incident.status === 'OPEN' ? '' : incident.updated_at, active: ['INVESTIGATING', 'RESOLVED', 'CLOSED'].includes(incident.status) },
    { label: 'Resolved', at: incident.resolved_at || '', active: ['RESOLVED', 'CLOSED'].includes(incident.status) },
    { label: 'Closed', at: incident.closed_at || '', active: incident.status === 'CLOSED' },
  ];
}

export function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params.incidentId ?? params.id;
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadIncident() {
    if (!incidentId) return;
    setLoading(true);
    try {
      const data = await api.getIncident(incidentId);
      setIncident(data);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load incident');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadIncident();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  if (!incidentId) {
    return <div className="error-banner">Incident id missing</div>;
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  if (loading || !incident) {
    return (
      <section className="page detail-page">
        <div className="panel detail-hero">
          <Skeleton width="22%" height={12} />
          <Skeleton width="54%" height={32} />
          <Skeleton width="72%" height={16} />
          <Skeleton width="92%" height={16} />
        </div>
      </section>
    );
  }

  const timeline = buildTimelineFromTransitions(incident);

  return (
    <section className="page detail-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Incident details</p>
          <h2>{incident.title}</h2>
          <p className="page-subtitle">Full incident record, timeline, raw signals, and RCA workflow.</p>
        </div>
        <Link className="secondary-link" to="/">
          Back to dashboard
        </Link>
      </div>

      <div className="panel detail-hero">
        <div className="detail-hero__summary">
          <div className="detail-hero__title-row">
            <SeverityBadge severity={incident.severity} />
            <span className={`status status-${incident.status.toLowerCase()}`}>{incident.status}</span>
          </div>
          <code className="incident-id">{incident.id}</code>
          <p className="detail-hero__component">{incident.component_id}</p>
        </div>
        <div className="detail-hero__stats">
          <article>
            <span>Created</span>
            <strong>{formatTime(incident.opened_at)}</strong>
          </article>
          <article>
            <span>Resolved</span>
            <strong>{formatTime(incident.resolved_at)}</strong>
          </article>
          <article>
            <span>Closed</span>
            <strong>{formatTime(incident.closed_at)}</strong>
          </article>
          <article>
            <span>Signals</span>
            <strong>{incident.signal_count}</strong>
          </article>
          <article>
            <span>MTTR</span>
            <strong>{incident.mttr_seconds ? `${Math.round(incident.mttr_seconds)}s` : 'In progress'}</strong>
          </article>
        </div>
      </div>

      <div className="panel workflow-panel">
        <div className="panel-heading">
          <h3>Incident workflow</h3>
          <p>OPEN → INVESTIGATING → RESOLVED → CLOSED</p>
        </div>
        <div className="workflow-track" aria-label="Incident workflow progression">
          {timeline.filter(step => step.at).map(step => (
            <div className={`workflow-step ${step.active ? 'active' : ''}`} key={step.label}>
              <span className="workflow-step__dot" />
              <div>
                <strong>{step.label}</strong>
                <small>{formatTime(step.at)}</small>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <h3>Linked raw signals</h3>
          <p>NoSQL events correlated to this incident.</p>
        </div>
        <div className="signal-list">
          {incident.raw_signals.length > 0 ? (
            incident.raw_signals.map(signal => (
              <article className="signal-item" key={signal.signal_id}>
                <div className="signal-item__header">
                  <strong>{signal.summary}</strong>
                  <span className={`severity severity-${signal.severity.toLowerCase()}`}>{signal.severity}</span>
                </div>
                <p className="signal-meta">
                  <span>{signal.source}</span>
                  <span>{formatTime(signal.occurred_at)}</span>
                </p>
                <pre className="signal-payload">{JSON.stringify(signal.payload, null, 2)}</pre>
              </article>
            ))
          ) : (
            <div className="empty-inline">No raw signals are linked to this incident yet.</div>
          )}
        </div>
      </div>

      {incident.rca ? (
        <div className="panel">
          <div className="panel-heading">
            <h3>Recorded RCA</h3>
            <p>This incident has already been closed with RCA.</p>
          </div>
          <div className="rca-summary">
            <p><strong>Category:</strong> {incident.rca.root_cause_category}</p>
            <p><strong>Summary:</strong> {incident.rca.root_cause_summary}</p>
            <p><strong>Fix applied:</strong> {incident.rca.fix_description}</p>
            <p><strong>Prevention steps:</strong> {incident.rca.prevention_plan}</p>
          </div>
        </div>
      ) : (
        <RcaForm incidentId={incident.id} onSaved={loadIncident} />
      )}
    </section>
  );
}
