import { Link } from 'react-router-dom';
import { SeverityBadge } from './SeverityBadge';
import type { IncidentSummary } from '../types';

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

export function IncidentCard({
  incident,
  highlight = false,
}: {
  incident: IncidentSummary;
  highlight?: boolean;
}) {
  const createdAt = incident.created_at ?? incident.opened_at;

  return (
    <Link className={`incident-card ${highlight ? 'incident-card--flash' : ''}`} to={`/incident/${incident.id}`}>
      <div className="incident-card__top">
        <SeverityBadge severity={incident.severity} />
        <span className={`status status-${incident.status.toLowerCase()}`}>{incident.status}</span>
      </div>
      <div className="incident-card__identity">
        <h3>{incident.title}</h3>
        <code>{incident.id}</code>
      </div>
      <p>{incident.component_id}</p>
      <dl>
        <div>
          <dt>Created</dt>
          <dd>{timeFormatter.format(new Date(createdAt))}</dd>
        </div>
        <div>
          <dt>Signals</dt>
          <dd>{incident.signal_count}</dd>
        </div>
        <div>
          <dt>MTTR</dt>
          <dd>{incident.mttr_seconds ? `${Math.round(incident.mttr_seconds)}s` : 'n/a'}</dd>
        </div>
      </dl>
    </Link>
  );
}
