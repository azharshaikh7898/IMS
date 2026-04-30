# Low-Level Design

## Entities

- Signal: raw incoming signal stored in MongoDB.
- Incident: source-of-truth work item stored in PostgreSQL.
- RCA: mandatory root cause analysis record stored in PostgreSQL.
- IncidentSignalLink: join table for traceability.
- IncidentMetric: aggregation row for operational reporting.

## Request Flow

1. Producer submits `SignalIngestRequest`.
2. API validates and rate-limits the request.
3. Raw signal is persisted to MongoDB.
4. The payload is appended to Redis Streams.
5. Worker consumes the stream and debounces by component.
6. New incident is created if the debounce window is open.
7. Dashboard clients receive a WebSocket event.

## Debounce Algorithm

- Key: `debounce:incident:{component_id}`.
- First signal in the window acquires a distributed lock and creates the incident.
- Subsequent signals reuse the stored incident id while the TTL remains active.
- After TTL expiry, the next signal starts a new window.

## State Transition Rules

- `OPEN -> INVESTIGATING`
- `OPEN -> RESOLVED`
- `INVESTIGATING -> RESOLVED`
- `RESOLVED -> CLOSED` only if RCA exists
- `CLOSED` is terminal

## Indexing Strategy

### PostgreSQL

- Incidents: index on `component_id`, `severity`, `status`, `updated_at`.
- RCA: unique index on `incident_id`.
- Metrics: composite index on `metric_name` and `bucket_ts`.

### MongoDB

- Raw signals: index on `signal_id`, `incident_id`, `component_id`, `occurred_at`.

### Redis

- Debounce keys use TTL expiration.
- Rate-limit keys are per client and per minute bucket.
- Sorted sets can cache dashboard ordering.

## Query Patterns

- Latest incidents by severity for the dashboard.
- Incident detail page by incident id.
- Raw signals linked to a single incident.
- RCA lookup by incident id.
- Timeseries metrics by hour or day.
