# EvalGate application threat model

- Review scope: EG-013A application security and privacy
- Review state: Implemented and locally testable; independent review and deployment review pending
- Protected assets: provider credentials, database integrity, governed corpus/index identities,
  evaluation evidence, user content confidentiality, and bounded server resources

## Trust boundaries and threats

| Boundary / threat | Control in EG-013A | Verification | Residual risk / owner |
|---|---|---|---|
| Browser input to HTTP API: oversized or malformed content | Streaming 16 KiB body cap, Pydantic field/token/page limits, content-free errors, total request timeout | HTTP bound/failure tests | Distributed volume, concurrency, token/day/cost limits and kill switch remain EG-013C |
| Browser rendering: XSS or invalid scheme | React text rendering, no raw HTML, citations are buttons tied to server-derived evidence, restrictive CSP | Component payload test plus existing citation tests | Full browser/content-safety and manual accessibility audit remains EG-013B |
| Corpus/provider prompt injection | Structured prompt separates system policy, question, and untrusted evidence; provider output accepts evidence IDs only; server revalidates citations | Existing injection-fixture and spoofed-citation tests | A model may still follow malicious evidence or produce plausible unsupported prose; live evidence is advisory and limitation-heavy |
| Public caller to privileged mutation | Explicit public route allowlist; no HTTP ingestion/import/evaluation trigger; environment matrix denies their command entrypoints | Route/capability integration tests | No authentication/RBAC is introduced; host-level exposure remains EG-016 |
| Client/proxy identity spoofing | Forwarding metadata trusted only from configured literal edge IPs; malformed/untrusted metadata rejected | Proxy unit/integration tests | Host-specific proxy chain and multi-hop semantics must be decided and verified in EG-016 |
| Raw IP privacy | Address is HMAC-keyed into a rotating short-lived pseudonym and is neither logged nor persisted | Determinism/rotation/redaction tests | EG-013C must ensure any future telemetry retains the same prohibition and bounded TTL |
| Outbound SSRF or credential exfiltration | OpenRouter base endpoint exact allowlist validated in Settings and adapter construction; secret remains server-side | Configuration and adapter tests | Provider redirects/DNS infrastructure remain external-service risks; no public live adapter is composed |
| Cross-origin browser abuse | Exact HTTPS public origins, no credentialed CORS, restrictive response headers | Accepted/rejected preflight and header tests | CORS is not authentication and cannot stop direct non-browser traffic |
| Sensitive content in logs/errors/database | Uvicorn access log disabled; request content never logged; safe problem bodies; public ask/search do not persist content | Marker tests and route/data-flow review | Infrastructure/provider logs and retention require host/provider verification before deployment |
| Secret committed to repository | `.env` ignored, example contains placeholders, publication scan detects selected token families and credential URLs | Publication check | Pattern scanning is not proof of secret absence; EG-013D adds a dedicated scanner and finding review |

## Data flow

```text
caller -> route/body/proxy/time boundary -> validated search or ask use case
       -> governed PostgreSQL evidence -> JSON or validated SSE

socket/forwarded address -> trusted-edge check -> keyed TTL pseudonym -> request state only

server Settings -> exact OpenRouter allowlist -> EG-015 protected evaluation adapter only
```

No public question, answer, retrieved chunk, raw address, authorization header, or provider key is
written by this flow. Evaluation result pages contain only explicitly reviewed imported artifacts
and their synthetic golden-case questions; public requests cannot create or import those records.

## Review conclusion

The application boundary now fails closed for the EG-013A threats above. It is not ready for public
deployment because layered usage/cost controls, kill switch, full browser/accessibility review,
release image/scans/SBOM, host-specific proxy/TLS/log-retention evidence, and deployment approval are
still open in EG-013B/C/D, EG-014, and optional EG-016.

