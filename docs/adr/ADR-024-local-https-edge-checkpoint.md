# ADR-024: Local HTTPS edge verification

Status: accepted for a local Phase 15 engineering checkpoint, 2026-09-26.
This is not remote-deployment approval.

## Context

The development Compose nginx serves HTTP on loopback. Its former
`$proxy_add_x_forwarded_for` setting appended a caller-supplied IP, and Uvicorn's
default proxy-header handling could make a forwarded value authoritative under
some network arrangements. The existing application has exact Origin, CSRF and
TrustedHost checks, but TestClient cannot exercise TLS termination, CSP, headers
or edge limits.

## Decision

Keep the existing HTTP Compose setup local. Add a separate production frontend
image configuration with one explicit lower-case DNS hostname and mounted TLS
certificate/key. The entrypoint fails if the hostname is malformed or the files
are unreadable, renders only that hostname, and checks nginx syntax before
starting. Unknown TLS SNI is rejected at handshake; an unexpected HTTP Host
receives 421. The known HTTP host redirects to HTTPS. The HTTPS host sets HSTS,
CSP, no-sniff and no-referrer headers. TLS 1.2/1.3 is configured.

Nginx is the intended direct client-facing edge. It replaces Host,
`X-Forwarded-Proto`, `X-Forwarded-For` and `X-Real-IP`, and removes
`X-Forwarded-Host` and `Forwarded` before proxying. The backend container now
starts Uvicorn with `--no-proxy-headers`, so incoming forwarded headers do not
change its scheme or client identity. The development nginx also replaces these
headers. A different upstream proxy would require a new reviewed trust topology;
do not assume the current per-IP limits remain meaningful behind one.

The candidate edge caps bodies at 16 KiB; sets client-header/body, keepalive,
send and upstream connect/send/read timeouts; and uses shared per-IP API request,
login request and concurrent-request limits. The 10 requests/second general
rate, 1 login request/second and bursts of 20/3 are authored operating limits,
not load-tested capacity or abuse-resistance metrics. PostgreSQL's login throttle
remains independent. There is no claim of a distributed limit across instances.
The nginx timeout directives bound idle intervals, not total wall-clock request
duration; an end-to-end deadline and load-budget verification remain open.

## Local verification and limits

With Homebrew nginx 1.31.4, a one-day self-signed certificate, a disposable
`*_test` PostgreSQL database, Uvicorn with proxy headers disabled and the built
frontend, the rendered config passed `nginx -t`. Real HTTPS requests returned
the frontend with CSP/HSTS; unexpected Host returned 421; wrong Origin returned
403; a valid local login returned `__Host-` Secure/HttpOnly cookies and a usable
session. A 20,000-byte body returned 413, repeated login requests reached 429,
and the known HTTP host redirected with 308. A separate temporary echo upstream
confirmed forged forwarded host/IP/protocol headers were overwritten or removed.
The certificate, session cookies, processes and temporary database were removed.

The smoke used the app's test environment and a disposable database. It did not
combine the edge with the four-role production database topology. The Docker
Desktop app on this host lacks a launchable executable and the engine is
unavailable, so the pinned nginx container image and production entrypoint have
not run here. No public hostname, trusted certificate, real client network,
load budget, secret manager, monitoring or operational recovery was tested.
Actual deployment review, MFA, verified human recovery and independent security
assessment remain mandatory before any remote exposure.

References: [nginx request limits](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html),
[connection limits](https://nginx.org/en/docs/http/ngx_http_limit_conn_module.html),
[proxy headers](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[TLS handshake rejection](https://nginx.org/en/docs/http/ngx_http_ssl_module.html).
