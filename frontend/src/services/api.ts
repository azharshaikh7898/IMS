import type { IncidentDetail, IncidentStatus, IncidentSummary } from '../types';
import { mockApi } from './mockApi';

const base = '/api';
let forceMockMode = false;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listIncidents: async (limit = 100) => {
    if (forceMockMode) return mockApi.listIncidents(limit);
    try {
      const data = await request<IncidentSummary[]>(`/incidents?limit=${limit}`);
      if (data.length === 0) {
        forceMockMode = true;
        return mockApi.listIncidents(limit);
      }
      return data;
    } catch {
      forceMockMode = true;
      return mockApi.listIncidents(limit);
    }
  },
  getIncident: async (id: string) => {
    if (forceMockMode) return mockApi.getIncident(id);
    try {
      return await request<IncidentDetail>(`/incidents/${id}`);
    } catch {
      forceMockMode = true;
      return mockApi.getIncident(id);
    }
  },
  updateStatus: async (id: string, target_status: IncidentStatus, notes?: string) => {
    if (forceMockMode) return mockApi.updateStatus(id, target_status, notes);
    try {
      return await request<IncidentSummary>(`/incidents/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ target_status, notes }),
      });
    } catch {
      forceMockMode = true;
      return mockApi.updateStatus(id, target_status, notes);
    }
  },
  createRca: (
    id: string,
    payload: {
      root_cause_category: string;
      root_cause_summary: string;
      fix_description: string;
      prevention_plan: string;
      occurred_at: string;
      detected_at: string;
    },
  ) => {
    if (forceMockMode) return Promise.resolve(mockApi.createRca(id, payload));
    return request<IncidentSummary>(`/incidents/${id}/rca`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }).catch(() => {
      forceMockMode = true;
      return mockApi.createRca(id, payload);
    });
  },
  closeIncident: async (id: string) => {
    if (forceMockMode) return mockApi.closeIncident(id);
    try {
      return await request<IncidentSummary>(`/incidents/${id}/close`, { method: 'POST' });
    } catch {
      forceMockMode = true;
      return mockApi.closeIncident(id);
    }
  },
  isMockMode: () => forceMockMode,
};