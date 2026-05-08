# Security

FundamenTracker is designed for self-hosting. Treat the API as private by default, especially when it is reachable through a public domain or Cloudflare Tunnel.

## API Authentication

Configure a long random token:

```env
API_AUTH_TOKEN=replace-with-a-long-random-token
```

Clients call protected endpoints with:

```text
Authorization: Bearer <API_AUTH_TOKEN>
```

If `API_AUTH_TOKEN` is missing, protected endpoints cannot be used successfully. Do not commit real tokens to the repository.

## Public Endpoints

These endpoints are public by design:

```text
GET /health/live
GET /server-time
GET /search
GET /market-overview
```

`GET /health/live` only reports that the FastAPI process is running and is suitable for container liveness checks.

`GET /health/ready` is protected by default because it reports operational readiness and database backend status. Set this only when you intentionally want unauthenticated readiness checks:

```env
PUBLIC_READY_HEALTH=true
```

## Protected By Default

These read endpoints require `Authorization: Bearer <API_AUTH_TOKEN>` by default:

```text
GET /watchlist
GET /alert-history
GET /scan-settings
GET /data/providers/health
GET /metric-current
GET /history
GET /health/ready
GET /ops/status
```

Mutable endpoints such as alert CRUD, `/scan`, `/scan-settings`, `/add`, and
`/remove` are protected. The AI endpoint `POST /ai-valuation` is also protected
because it can call a paid/limited external model and expose portfolio context.

`GET /watchlist` can be made public with:

```env
READONLY_PUBLIC=true
```

Only use this on a trusted network or behind another access layer. The watchlist reveals portfolio interests, alert configuration, and tracked metrics.

## Frontend Token Note

`VITE_API_AUTH_TOKEN` is embedded into the browser bundle. It is convenient for a private bundled frontend, but it is not strong authentication for a public website. For internet-facing deployments, put the frontend and API behind Cloudflare Access, a VPN, or real user authentication.

For deployment patterns and a public exposure checklist, see [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md).

## CORS

Use exact frontend origins:

```env
CORS_ALLOWED_ORIGINS=https://your-frontend.example.com
ALLOW_WILDCARD_CORS=false
```

Do not use wildcard CORS on public deployments unless you have a separate access-control layer and understand the exposure.

## Dashboards And Host Operations

Do not expose pgAdmin/Adminer or host control endpoints publicly. The project should not provide public HTTP endpoints that restart Docker, systemd, or host services. Use systemd, the local watchdog, SSH, VPN, or a private admin network for host operations.
