# Public-mode application security

EG-013A implements the application-side portion of ADR-0009. It is a tested security boundary,
not a deployment, penetration test, WAF, authentication system, or claim that anonymous live
generation is ready. EG-013C must still add provider-neutral usage/concurrency controls and a kill
switch; EG-016 remains the separate host and deployment decision.

## Environment capability matrix

| Environment | Corpus ingestion | Result import | Evaluation command | Public HTTP policy |
|---|---:|---:|---:|---:|
| `local` | Yes | Yes | Yes | No |
| `ci` | Yes | No | Yes | No |
| `trusted_evaluation` | No | No | Yes | No |
| `public` | No | No | No | Yes |

The matrix is defined in the framework-free application layer and checked by the ingestion,
result-import, evaluation, live-evaluation, and HTTP entrypoints. HTTP has no ingestion, import, or
evaluation-trigger route. In public mode, only liveness/readiness, read-only search/ask operations,
and read-only evaluation-result queries are admitted; documentation and unknown/mutation-shaped
paths return a content-free `404`.

Public `/api/v1/ask` remains fail-closed at this stage: the HTTP adapter does not compose the
EG-015 live-evaluation adapter, and non-fixture generation is rejected by the existing answer-route
mode check. It must not be enabled until EG-013C and any EG-016 deployment gates pass.

## HTTP and outbound boundary

- JSON request bodies are limited to 16 KiB by default while ASGI chunks arrive, including when
  `Content-Length` is absent. Search/ask fields and evaluation-result cursors/page sizes retain their
  stricter contract limits.
- A 30-second default server timeout wraps the complete ASGI response lifecycle. A timeout before
  headers is a content-free `504`; after streaming starts, the request is cancelled and closed.
- Browser CORS uses exact configured origins, never a wildcard or credentialed CORS. Public origins
  must use HTTPS and contain no credentials, path, query, or fragment.
- Responses include a deny-by-default CSP, anti-framing, MIME-sniffing, referrer, browser-feature,
  opener, cache, and (public-only) HSTS policy.
- Public forwarding headers are rejected unless the socket peer is an explicitly configured literal
  proxy IP. Only the first valid forwarded client IP is then accepted for rate identity.
- The raw rate address is immediately transformed with a server-only HMAC key and rotating TTL
  bucket. Only the short-lived pseudonym is attached to request state; EG-013A does not log it or
  persist it. EG-013C may consume this interface for bounded in-memory controls.
- The OpenRouter adapter accepts only `https://openrouter.ai/api/v1`. Alternate schemes, hosts,
  credentials, queries, fragments, loopback endpoints, and arbitrary URLs fail before a request.

## Configuration

Local mode works with `.env.example` defaults. Public mode additionally requires:

```dotenv
EVALGATE_ENVIRONMENT=public
EVALGATE_ALLOWED_ORIGINS=https://evalgate.example
EVALGATE_RATE_IDENTITY_SECRET=<random server-side value of at least 32 bytes>
EVALGATE_TRUSTED_PROXY_ADDRESSES=<optional comma-separated literal edge IPs>
EVALGATE_EMBEDDING_MODE=reference
EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT=<verified local snapshot>
EVALGATE_GENERATION_MODE=disabled
```

The real rate secret belongs in a local ignored environment file or a future host secret store; it
must never be committed or sent to the browser. Proxy addresses cannot be chosen until a host is
approved. Access logging remains disabled.

## Verification scope

Automated tests cover the environment and route matrices, exact CORS, security headers, body and
time bounds, trusted proxy behavior, rotating pseudonyms, provider-endpoint SSRF configuration,
content-free errors/logs, inert React rendering of XSS/invalid-scheme text, citation spoof rejection,
and indirect-injection prompt separation. `scripts/check_publication.py` also rejects publication of
machine paths, email addresses, credential-bearing URLs, OpenRouter keys, and GitHub tokens.

