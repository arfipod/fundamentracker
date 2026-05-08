# FundamenTracker Frontend

This directory contains the current React/Vite frontend for FundamenTracker. It
is the browser UI for reviewing signals, managing watchlist alerts, running
scans, exploring metrics, viewing charts, and requesting Gemini analysis
through the backend.

## Tech Stack

- React 19
- Vite 8
- TypeScript 6
- Recharts
- Plain CSS in `src/App.css` and `src/index.css`

`package.json` currently lists no icon library. Some components use inline SVG
icons.

## Structure

- `src/App.tsx`: top-level Signals/Watchlist/Explorer tab layout.
- `src/lib/apiClient.ts`: shared API fetch helper and bearer-token injection.
- `src/types/watchlist.ts`: watchlist, alert, and alert-history TypeScript
  types.
- `src/types/signals.ts`: Signal Inbox TypeScript types.
- `src/hooks/useWatchlist.ts`: watchlist loading plus alert/ticker mutations and
  undo behavior.
- `src/hooks/useScanSettings.ts`: scan interval, manual scan, and server time.
- `src/components/AlertForm.tsx`: add-alert form with ticker autocomplete.
- `src/components/SignalInbox.tsx`: open signal list with acknowledge, dismiss,
  and refresh controls.
- `src/components/WatchlistSection.tsx`: table/grid watchlist display, sorting,
  and backend tag filtering.
- `src/components/TickerRow.tsx`: table-row ticker view.
- `src/components/TickerCard.tsx`: card ticker view.
- `src/components/AlertItem.tsx`: alert display, target edit, toggle, delete,
  relative-diff display, data-quality badge, and chart expansion.
- `src/components/DataQualityBadge.tsx`: compact source, stale, timestamp, and
  confidence display for current metric values.
- `src/components/MetricChart.tsx`: historical metric chart using Recharts.
- `src/components/ExplorerSection.tsx`: standalone ticker/metric explorer.
- `src/components/DashboardHeader.tsx`: scan controls and timing display.

## Environment Variables

For local frontend development, create `frontend/.env.local` or use the root
Compose `.env` values:

```env
VITE_API_URL=http://localhost:8000
VITE_API_AUTH_TOKEN=change-me-api-token
```

`VITE_API_URL` defaults to `http://localhost:8000` in `apiClient.ts` when it is
not set.

`VITE_API_AUTH_TOKEN` is sent as:

```text
Authorization: Bearer <token>
```

Vite embeds `VITE_*` values into browser assets. This token is only a convenience
for private deployments, local development, Cloudflare Access, or VPN-protected
frontends. Do not rely on it as strong authentication for a public unprotected
frontend.

`apiClient.ts` also supports a runtime browser config object:

```ts
window.__FUNDAMENTRACKER_CONFIG__ = {
  API_AUTH_TOKEN: "...",
};
```

The current production Dockerfile does not generate that runtime config; it uses
build arguments for `VITE_API_URL` and `VITE_API_AUTH_TOKEN`.

## Running Locally

Install dependencies:

```bash
npm ci
```

Start the Vite dev server:

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

The backend must be reachable at `VITE_API_URL`.

## Validation

Build:

```bash
npm run build
```

Lint command:

```bash
npm run lint
```

Known current limitation: lint is not enforced in CI because it currently fails
on existing React hooks and TypeScript lint issues.

There is no `npm test` script and no committed frontend unit test suite at the
moment.

## Current Behavior Notes

- Tags and basic ticker metadata are persisted by the backend and returned in
  the watchlist response.
- Alert current values and Explorer current metric values show data-quality
  metadata from the backend, including source, stale status, fetched/as-of
  timestamps, expiry, and confidence when available.
- Watchlist reads and all mutable operations use `apiFetch`.
- Alert update/delete/toggle calls use alert IDs.
- The AI valuation UI expects the backend response shape
  `{"analysis": "..."}`.
