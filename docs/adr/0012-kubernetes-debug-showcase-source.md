# ADR-0012: Kubernetes debug documentation showcase source

- Status: Accepted for EG-018 source ingestion and local retrieval evidence
- Date: 2026-09-18
- Story: EG-018

## Context

EvalGate needs one real-world documentation showcase that demonstrates governed RAG mechanics without becoming a crawler, benchmark marketplace, or production-traffic claim. The source must be small, licensed, immutable, attributable, and safe to inspect in a public repository.

The repository owner approved only the Kubernetes website source directory `content/en/docs/tasks/debug/debug-cluster/` at commit `aa4e9e6dee49106155072a44ef997b91722243ec`, including its 11 Markdown files, under CC BY 4.0.

## Decision

Vendor the approved Kubernetes website debug-cluster Markdown files under `data/third_party/kubernetes-debug-cluster/documents/` with a separate manifest at `data/manifests/kubernetes-debug-cluster-v1.json`.

The snapshot records:

- upstream repository `https://github.com/kubernetes/website`;
- upstream commit `aa4e9e6dee49106155072a44ef997b91722243ec`;
- approved source path `content/en/docs/tasks/debug/debug-cluster/`;
- the 11 approved Markdown filenames only;
- CC BY 4.0 license text copied as `data/third_party/kubernetes-debug-cluster/CC-BY-4.0.txt`;
- attribution to The Kubernetes Authors;
- transformation disclosure: strict UTF-8, Unicode NFC, CRLF/CR converted to LF, Kubernetes site-root Markdown links converted to absolute https://kubernetes.io/docs/... URLs, exactly one terminal LF, no semantic edits;
- no endorsement/trademark text: Kubernetes is a trademark of The Linux Foundation, and EvalGate is not endorsed by or affiliated with Kubernetes, CNCF, or The Linux Foundation.

Use a separate `kubernetes-debug-heading-v1` chunking policy. H2/H3 headings define semantic sections; sections over 512 reference-token budget split at blank-line paragraph boundaries into consecutive reconstructive parts. Northstar keeps `northstar-heading-v1` unchanged.

The curated dataset `contracts/evaluation/kubernetes-debug-v1.json` is EvalGate-authored and human-reviewed demonstration data. It is not production-user traffic and not an external benchmark.

## Consequences

The corpus loader now supports registered corpus definitions with per-corpus roots, license gates, document/chunk bounds, and chunking policy identities. Arbitrary paths, runtime URL fetches, broad mirrors, images, generated API reference content, and endorsement implications remain prohibited.

Northstar corpus files, chunking policy, manifest identity, and regression baseline are not changed by this decision.

OpenRouter model comparison remains gated. This ADR does not authorize any provider call, corpus egress, budget spend, fallback, browser secret, deployment, push, merge, tag, or release.

## Verification

EG-018 verifies source schema, license text, exact document layout, normalized hashes, reconstructive chunks, reviewed dataset split mix, and fixture artifact schema compatibility. Later EG-018 provider work must reverify model availability, price, structured-output support, ZDR/data-collection denial routing, and obtain separate owner approval before any external call.