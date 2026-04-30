import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { IncidentCard } from '../components/IncidentCard';
import { Skeleton } from '../components/Skeleton';
import { useIncidentStream } from '../hooks/useIncidentStream';
import type { IncidentSummary } from '../types';

const severityRank = { P0: 0, P1: 1, P2: 2 } as const;
const severityOptions = ['ALL', 'P0', 'P1', 'P2'] as const;

function matchesQuery(incident: IncidentSummary, query: string): boolean {
  if (!query) return true;
  const value = query.toLowerCase();
  return [incident.id, incident.component_id, incident.title, incident.status, incident.severity].some(field => field.toLowerCase().includes(value));
}

export function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [query, setQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<(typeof severityOptions)[number]>('ALL');
  const { incidents, setIncidents, connected, highlightedIds } = useIncidentStream([] as IncidentSummary[]);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const data = await api.listIncidents();
        if (!cancelled) {
          setIncidents(data);
          setDemoMode(api.isMockMode());
          setError(null);
        }
      } catch (requestError) {
        if (!cancelled) {
          setDemoMode(api.isMockMode());
          setError(requestError instanceof Error ? requestError.message : 'Unable to load incidents');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [setIncidents]);

  const filteredIncidents = incidents
    .filter(incident => (severityFilter === 'ALL' ? true : incident.severity === severityFilter))
    .filter(incident => matchesQuery(incident, query))
    .sort((left, right) => severityRank[left.severity] - severityRank[right.severity] || +new Date(right.opened_at) - +new Date(left.opened_at));

  return (
    <section className="page">
      <header className="page-header dashboard-header">
        <div>
          <p className="eyebrow">Live incidents</p>
          <h2>
            Live incident feed
            {demoMode ? (
              <span
                className="demo-badge"
                role="note"
                tabIndex={0}
                aria-label="Demo mode is enabled because live incident API returned no incidents or failed."
              >
                Demo mode
                <span className="demo-tooltip" role="tooltip">
                  Showing seeded demo incidents because the live incident API returned no records or was unavailable.
                </span>
              </span>
            ) : null}
          </h2>
          <p className="page-subtitle">Streaming from the backend API with WebSocket updates and polling fallback.</p>
        </div>
        <div className="dashboard-status">
          <div className={`connection ${connected ? 'live' : 'offline'}`}>{connected ? 'WebSocket live' : 'Polling fallback'}</div>
          <span className="status-note">Sorted by P0, P1, P2</span>
        </div>
      </header>

      <div className="panel filters-panel">
        <label className="filter-field">
          Search
          <input
            type="search"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Incident ID, component, title, severity, or status"
          />
        </label>
        <label className="filter-field">
          Severity
          <select value={severityFilter} onChange={event => setSeverityFilter(event.target.value as (typeof severityOptions)[number])}>
            <option value="ALL">All severities</option>
            <option value="P0">P0</option>
            <option value="P1">P1</option>
            <option value="P2">P2</option>
          </select>
        </label>
        <div className="filter-summary">
          <strong>{filteredIncidents.length}</strong>
          <span>visible of {incidents.length} incidents</span>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {loading ? (
        <div className="incident-grid">
          {Array.from({ length: 6 }).map((_, index) => (
            <div className="panel incident-skeleton" key={index}>
              <Skeleton width="36%" height={12} />
              <Skeleton width="78%" height={24} />
              <Skeleton width="64%" height={14} />
              <Skeleton width="92%" height={12} />
            </div>
          ))}
        </div>
      ) : filteredIncidents.length > 0 ? (
        <div className="incident-grid">
          {filteredIncidents.map(incident => (
            <IncidentCard incident={incident} key={incident.id} highlight={Boolean(highlightedIds[incident.id])} />
          ))}
        </div>
      ) : (
        <div className="panel empty-state">
          <h3>No active incidents</h3>
          <p>No incidents match the current filters.</p>
        </div>
      )}
    </section>
  );
}
