import { useEffect, useState } from 'react';
import type { IncidentSummary } from '../types';

export function useIncidentStream(initial: IncidentSummary[]) {
  const [incidents, setIncidents] = useState(initial);
  const [connected, setConnected] = useState(false);
  const [highlightedIds, setHighlightedIds] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const candidates = [
      `${protocol}//localhost:8000/ws`,
      `${protocol}//${window.location.host}/ws`,
    ];

    const cleanup: Array<() => void> = [];
    let socket: WebSocket | null = null;

    const connect = (index: number) => {
      const target = candidates[Math.min(index, candidates.length - 1)];
      socket = new WebSocket(target);

      socket.onopen = () => setConnected(true);
      socket.onerror = () => {
        if (index + 1 < candidates.length) {
          connect(index + 1);
        }
      };
      socket.onclose = () => setConnected(false);
      socket.onmessage = event => {
        const payload = JSON.parse(event.data) as { event_type: string; incident: IncidentSummary };
        setIncidents(current => {
          const next = current.filter(item => item.id !== payload.incident.id);
          return [payload.incident, ...next].sort((left, right) => {
            const severityRank = { P0: 0, P1: 1, P2: 2 } as const;
            return severityRank[left.severity] - severityRank[right.severity] || +new Date(right.opened_at) - +new Date(left.opened_at);
          });
        });
        setHighlightedIds(current => ({ ...current, [payload.incident.id]: true }));
        const timer = window.setTimeout(() => {
          setHighlightedIds(current => {
            const next = { ...current };
            delete next[payload.incident.id];
            return next;
          });
        }, 3000);
        cleanup.push(() => window.clearTimeout(timer));
      };
    };

    connect(0);

    return () => {
      if (socket) socket.close();
      cleanup.forEach(fn => fn());
    };
  }, []);

  return { incidents, setIncidents, connected, highlightedIds };
}
