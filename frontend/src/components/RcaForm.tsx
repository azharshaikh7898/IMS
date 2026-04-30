import { useState, type FormEvent } from 'react';
import { api } from '../services/api';

type RcaFieldState = {
  startTime: string;
  endTime: string;
  rootCauseCategory: string;
  fixApplied: string;
  preventionSteps: string;
};

const emptyState: RcaFieldState = {
  startTime: '',
  endTime: '',
  rootCauseCategory: '',
  fixApplied: '',
  preventionSteps: '',
};

function toIso(value: string): string {
  return new Date(value).toISOString();
}

export function RcaForm({
  incidentId,
  onSaved,
  disabled = false,
}: {
  incidentId: string;
  onSaved: () => void | Promise<void>;
  disabled?: boolean;
}) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fields, setFields] = useState<RcaFieldState>(emptyState);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled || saving) return;

    const trimmed = {
      startTime: fields.startTime.trim(),
      endTime: fields.endTime.trim(),
      rootCauseCategory: fields.rootCauseCategory.trim(),
      fixApplied: fields.fixApplied.trim(),
      preventionSteps: fields.preventionSteps.trim(),
    };

    if (!trimmed.startTime || !trimmed.endTime || !trimmed.rootCauseCategory || !trimmed.fixApplied || !trimmed.preventionSteps) {
      setMessage('All RCA fields are required.');
      return;
    }

    const payload = {
      root_cause_category: trimmed.rootCauseCategory,
      root_cause_summary: `${trimmed.rootCauseCategory}: ${trimmed.fixApplied}. ${trimmed.preventionSteps}`,
      fix_description: trimmed.fixApplied,
      prevention_plan: trimmed.preventionSteps,
      occurred_at: toIso(trimmed.startTime),
      detected_at: toIso(trimmed.endTime),
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createRca(incidentId, payload);
      await api.closeIncident(incidentId);
      setMessage('RCA submitted and incident closed');
      setFields(emptyState);
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to save RCA');
    } finally {
      setSaving(false);
    }
  }

  return disabled ? null : (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <div className="form-header">
        <div>
          <p className="eyebrow">Mandatory RCA</p>
          <h3>Close the incident with a documented analysis</h3>
        </div>
      </div>
      <div className="form-grid">
        <label>
          Start Time
          <input
            name="start_time"
            type="datetime-local"
            required
            value={fields.startTime}
            onChange={event => setFields(current => ({ ...current, startTime: event.target.value }))}
          />
        </label>
        <label>
          End Time
          <input
            name="end_time"
            type="datetime-local"
            required
            value={fields.endTime}
            onChange={event => setFields(current => ({ ...current, endTime: event.target.value }))}
          />
        </label>
        <label>
          Root Cause Category
          <select
            name="root_cause_category"
            required
            value={fields.rootCauseCategory}
            onChange={event => setFields(current => ({ ...current, rootCauseCategory: event.target.value }))}
          >
            <option value="" disabled>
              Select category
            </option>
            <option>Database</option>
            <option>Cache</option>
            <option>Network</option>
            <option>Deployment</option>
            <option>Dependency</option>
            <option>Code defect</option>
            <option>Configuration</option>
          </select>
        </label>
        <label>
          Fix Applied
          <textarea
            name="fix_applied"
            required
            rows={4}
            value={fields.fixApplied}
            onChange={event => setFields(current => ({ ...current, fixApplied: event.target.value }))}
          />
        </label>
        <label>
          Prevention Steps
          <textarea
            name="prevention_steps"
            required
            rows={4}
            value={fields.preventionSteps}
            onChange={event => setFields(current => ({ ...current, preventionSteps: event.target.value }))}
          />
        </label>
      </div>
      <div className="form-actions">
        <button className="primary" disabled={saving} type="submit">
          {saving ? 'Submitting...' : 'Submit RCA & Close'}
        </button>
        {message ? <span className="form-message">{message}</span> : null}
      </div>
    </form>
  );
}
