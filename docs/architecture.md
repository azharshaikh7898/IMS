# Architecture

## High-Level Diagram

```text
+---------------------+     +---------------------+     +----------------------+
| Signal Producers    | --> | FastAPI Ingestion   | --> | Redis Streams Queue  |
+---------------------+     +---------------------+     +----------------------+
                                      |                          |
                                      |                          v
                                      |                 +----------------------+
                                      |                 | Async Worker Pool    |
                                      |                 +----------------------+
                                      |                          |
                                      v                          v
                              +------------------+      +----------------------+
                              | MongoDB Raw Data  |      | PostgreSQL Source of |
                              | (signals)         |      | Truth (incidents,    |
                              +------------------+      | RCA, metrics)        |
                                      |                 +----------------------+
                                      |                          |
                                      v                          v
                              +------------------+      +----------------------+
                              | Redis Cache /     | <--> | WebSocket Dashboard  |
                              | PubSub            |      +----------------------+
                              +------------------+
```

## Component Responsibilities

### Producer Layer

- Accepts JSON signals from agents, monitors, and synthetic generators.
- Performs rate limiting before queue submission.
- Writes raw signal payloads to MongoDB for forensic traceability.

### Processing Layer

- Redis Streams buffers bursts up to tens of thousands of signals per second.
- Worker consumers debounce by `component_id` within a 10-second window.
- A distributed Redis lock prevents duplicate incident creation across worker replicas.

### Storage Layer

- MongoDB stores the raw signal feed and incident linkage metadata.
- PostgreSQL stores incidents, lifecycle status, RCA, and aggregation tables.
- Redis holds debounce leases, rate-limit counters, and dashboard cache state.

### Dashboard Layer

- WebSocket subscribers receive incident create/update events.
- The frontend sorts by severity and refreshes in real time.

## Low-Level Design

### Ingestion API

- `POST /api/signals` validates payload shape and severity.
- A Redis token bucket guards the ingestion edge.
- Signals are appended to a Redis Stream for durable async processing.

### Worker

- Consumes Redis Stream entries with consumer groups.
- Resolves the active component window through cache keys.
- Creates one incident per debounce window and increments signal counts for later events.

### Incident Workflow Engine

- `OPEN`: initial state after incident creation.
- `INVESTIGATING`: manual triage stage.
- `RESOLVED`: fix is confirmed but RCA may still be pending.
- `CLOSED`: allowed only after a valid RCA exists.

### RCA Enforcement

- The state engine blocks `CLOSED` transitions without RCA.
- RCA records require category, summary, fix, prevention, and timestamps.

### Observability

- `/api/health` checks Redis, MongoDB, and PostgreSQL connectivity.
- The API logs signals per 5 seconds.
- Stream lag and worker backlog can be added to the same metrics plane.

## Backpressure Strategy

- Reject abusive clients with rate limiting.
- Buffer burst traffic in Redis Streams.
- Scale worker replicas when queue lag increases.
- Use debounce keys to suppress duplicate incident fan-out.

## Fault Tolerance

- Worker retries can be added through Redis pending entry scanning or a retry stream.
- Database writes are isolated per repository and can be wrapped with exponential backoff.
- Redis lock failures degrade safely by preventing duplicate incident writes rather than corrupting state.

## Horizontal Scaling

- API instances scale statelessly.
- Worker replicas scale independently using Redis consumer groups.
- PostgreSQL can be read-scaled for dashboard queries.
- MongoDB handles raw signal write pressure separately from incident writes.
