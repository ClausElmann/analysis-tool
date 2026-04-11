# DOMAIN DISTILLATION — Monitoring
**Status:** APPROVED_BASELINE 2026-04-11
**Source:** Source-primary (Layer 1 score 0.20 — UI component files used)
**Authority:** INFORMATIONAL (Layer 1)

---

## 1. DOMAIN ROLE

Monitoring is a **SuperAdmin-only real-time operational dashboard** showing live job execution, geographic message activity, time-series delivery graphs, and a historical job log. Access restricted to super-admin users.

Controller: `BalarmWebApp.Controllers.SuperAdmin.Monitoring.MonitoringController` at `api/Monitoring/`

---

## 2. KEY ENTITIES

| Entity | Fields | Used in |
|---|---|---|
| `SeriesReadModel` | `graph: string`, `translationKey: string`, `color: string`, `values: SeriesValueReadModel[]` | `monitoring-graph` time-series chart |
| `SeriesValueReadModel` | `timestamp: string`, `value: number`, `note: string` | Individual data points within a graph series |
| `MapDataReadModel` | `longitude: number`, `latitude: number`, `seconds: number` | `monitoring-map` geographic activity display |
| `ProgressWatcherInfoDto` | `job: string`, + progress fields | `monitoring-dashboard` live SSE panel |
| `JobTaskDto` | jobTaskId, status, timing, etc. | `monitoring-jobs` historical job table |

---

## 3. BEHAVIORS

### 3a. Dashboard — live job progress (SSE)
- Subscribes to SSE channel for `ServerSentEventType.PROGRESSWATCHERINFO` events.
- Each event carries a `ProgressWatcherInfoDto` identified by `job` name.
- New jobs are appended to an in-memory list; updates replace existing rows (matched by `job`).
- When `job.complete === true`, the row auto-removes after a 30 second delay.
- Renders as an animated panel — BiCustomAnimations.fadeInOutChildren.

### 3b. Graph — time-series delivery volumes
- On load: `GET api/Monitoring/GetGraphData` → `SeriesReadModel[]`
- Each `SeriesReadModel` identifies a named graph (e.g. "SMS sent", "Delivery failed") with a color, translation key, and timestamped values.
- `monitoring-graph` component groups series by `graph` name and renders stacked bar chart (Chart.js with moment-timezone adapter).
- Zero-fill applied between sparse data points to maintain timeline continuity.
- Filters out series with all-zero values to keep chart readable.

### 3c. Map — geographic activity pings
- Polls `GET api/Monitoring/GetMapData` → `MapDataReadModel[]` every **15 seconds**.
- Each item has `(longitude, latitude, seconds)` — `seconds` = age of the most recent message sent to that geographic coordinate.
- Items with `seconds <= 15` are displayed as Leaflet "ping" animations (CSS class `leaflet-ping`).
- Map initializes centered on Scandinavia: LatLngBounds(`63.947N 35.09E` ↔ `53.814N 10.217E`).

### 3d. Jobs — recent and ongoing task log
- On load: `GET api/Jobs/GetRecentAndOngoingTasks` → `JobTaskDto[]` (borrowed from job_management domain's `JobsController`)
- Also subscribes to SSE `ServerSentEventType.ACTIVEJOBS` events — updates matching `jobTaskId` in the table in real-time.
- Displayed in sortable paginated table (`bi-p-table`) with multi-select filter.
- Click row → opens `TaskDetailsDialogContentComponent` dialog with full task detail.
- Uses `moment` for time formatting and `JobTaskStatusCode` enum for status display.

---

## 4. FLOWS

### Flow A — SuperAdmin opens Monitoring dashboard
1. Navigate to monitoring route (SuperAdmin only).
2. SSE connection is already open (managed by `ServerSentEventManagerService`).
3. Dashboard panel renders active ProgressWatcher jobs from SSE events.
4. Graph tab calls `GetGraphData` → time-series charts render.
5. Map tab starts 15s polling loop calling `GetMapData`; recent message coordinates appear as pings.
6. Jobs tab calls `GetRecentAndOngoingTasks` for initial load, then real-time updates via SSE.

### Flow B — Live job update on map and dashboard
1. A background job triggers `ProgressWatcherInfoDto` SSE events as it progresses.
2. Dashboard panel updates progress bar / completion status live.
3. When job publishes message coordinates → next `GetMapData` poll shows the ping.
4. When job completes → `ProgressWatcherInfoDto.complete = true` → dashboard removes row after 30 seconds.

---

## 5. RULES

1. **SuperAdmin only**: All Monitoring endpoints and UI routes are restricted to SuperAdmin role. No customer-facing exposure.

2. **SSE dependency**: The dashboard and jobs panels require an active SSE connection. If SSE drops, live updates stop but historical data (from initial load) remains visible.

3. **Map polls, does not push**: `GetMapData` is polled every 15 seconds — it is NOT SSE-driven. Only items with `seconds <= 15` are displayed as active pings; older items are silently ignored.

4. **GetRecentAndOngoingTasks is from job_management**: The Jobs tab in Monitoring borrows `api/Jobs/GetRecentAndOngoingTasks` from the `JobsController` (job_management domain). Monitoring owns the UI only; job_management owns the data.

5. **Graph data is static on load**: `GetGraphData` is called once on initial load — there is no polling or SSE refresh for graph data. The graph reflects the server state at the time of navigation.

6. **Graph zero-fill**: The graph component inserts zero values between sparse data points to prevent visual gaps in the bar chart timeline.
