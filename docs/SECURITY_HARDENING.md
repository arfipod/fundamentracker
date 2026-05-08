# Security Hardening

FundamenTracker is built for self-hosting. Treat the API and bundled frontend as private tools unless you intentionally put a stronger access layer in front of them.

## Frontend Token Limitation

`API_AUTH_TOKEN` protects backend endpoints by requiring:

```text
Authorization: Bearer <API_AUTH_TOKEN>
```

`VITE_API_AUTH_TOKEN` is different because it is a frontend build-time variable. Vite embeds every `VITE_*` value into the JavaScript, HTML, and assets served to the browser. Anyone who can load the frontend can inspect the built files or browser network requests and reuse that token.

This means `VITE_API_AUTH_TOKEN` is only suitable for trusted or private deployments, such as:

- a private LAN service used by household or lab devices you control
- a frontend already protected by Cloudflare Access
- a frontend reachable only through Tailscale, WireGuard, or another VPN
- local development

Do not rely on `VITE_API_AUTH_TOKEN` as strong security for an internet-facing public frontend. It is a convenience token for private deployments, not user authentication.

## Safe Deployment Modes

### Private LAN Only

Use this when FundamenTracker is reachable only from your home or lab network.

Recommended settings:

```env
API_BIND_IP=127.0.0.1
FRONTEND_BIND_IP=127.0.0.1
READONLY_PUBLIC=false
PUBLIC_READY_HEALTH=false
ALLOW_WILDCARD_CORS=false
```

Bind services to `127.0.0.1` when using a local reverse proxy on the host. If you intentionally bind to a LAN IP, restrict access with host firewall rules and do not forward the ports from your router.

`VITE_API_AUTH_TOKEN` is acceptable in this mode if every device that can load the frontend is trusted.

### Cloudflare Access

Use this when the app needs a public hostname but should only be available to approved users.

Recommended shape:

- expose the app through Cloudflare Tunnel
- put both the frontend hostname and API hostname behind Cloudflare Access
- require login with your identity provider before either hostname loads
- keep `READONLY_PUBLIC=false`
- keep `PUBLIC_READY_HEALTH=false` unless an authenticated monitor needs it
- keep CORS restricted to exact frontend origins

`VITE_API_AUTH_TOKEN` can still be used as a backend convenience token, but Cloudflare Access is the real public access control. Without Cloudflare Access or equivalent protection, anyone who loads the frontend can recover the Vite token.

### Tailscale, WireGuard, Or VPN

Use this when you want remote access without publishing FundamenTracker to the open internet.

Recommended shape:

- bind services to `127.0.0.1` or a private VPN interface
- allow access only from VPN clients
- avoid public DNS records that point directly to the host
- keep dashboard services such as pgAdmin bound to `127.0.0.1` unless explicitly needed on the VPN

`VITE_API_AUTH_TOKEN` is acceptable when the frontend is only reachable by trusted VPN peers.

### Future Login And Session Auth

The long-term public deployment model should use real user authentication, such as login plus server-managed sessions or another audited auth provider. In that model:

- the browser should not receive a reusable global API token
- mutable endpoints should be authorized per user/session
- secrets should stay server-side
- audit logs should identify the user or automation that changed data

Until that exists, do not run the bundled frontend as an unprotected public website.

## Public Deployment Checklist

Before exposing any hostname publicly:

- protect both frontend and API with Cloudflare Access, a VPN, or real login/session auth
- set a long random `API_AUTH_TOKEN`
- keep `VITE_API_AUTH_TOKEN` only for private or access-controlled frontends
- set `READONLY_PUBLIC=false`
- keep `PUBLIC_READY_HEALTH=false` unless you understand the readiness data exposure
- set `CORS_ALLOWED_ORIGINS` to exact origins, not `*`
- keep `ALLOW_WILDCARD_CORS=false`
- do not expose pgAdmin/Adminer through a public tunnel
- do not add public endpoints that restart Docker, systemd, or host services

## Related Docs

- [`SECURITY.md`](SECURITY.md) describes protected and public API endpoints.
- [`DEPLOYMENT_SEQUENCE.md`](DEPLOYMENT_SEQUENCE.md) describes production Compose and Cloudflare Tunnel deployment.
- [`HOST_SETUP.md`](HOST_SETUP.md) describes Linux host operation.
