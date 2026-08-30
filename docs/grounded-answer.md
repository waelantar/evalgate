# Grounded-answer core

EG-006 adds a transport-independent application use case over the accepted search and generation
ports. The reviewed prompt contract is
[`grounded-answer-v1`](../contracts/prompts/grounded-answer-v1.json). HTTP answer creation,
fetching, and streaming remain owned by EG-007.

## Data flow

1. The caller selects an immutable index version, retrieval limit, and explicit `retrieval_only`
   or `fixture` mode.
2. The existing search use case validates the question and index identities, embeds the question,
   and returns explainable hybrid evidence.
3. The answer policy truncates the ordered evidence set at reviewed retrieval, token, and code-point
   budgets. It serializes system policy, question, and evidence as separate JSON fields.
4. In fixture mode, the generation port returns only answer status, answer text, claim offsets, and
   evidence IDs. Retrieval-only mode never invokes generation.
5. The server rejects unknown evidence IDs and malformed associations, rechecks each stored span
   hash, and derives the title, source, provenance, license, offsets, hash, and bounded quote from
   retrieved evidence. Provider-supplied metadata or quotes are invalid output.

## Trust and privacy boundary

Evidence is explicitly untrusted data: instructions inside it cannot override the system policy,
enable tools, or authorize outside knowledge. Provider mode and identity are explicit. A timeout,
provider failure, malformed output, missing citation, spoofed citation, or evidence-integrity
failure produces a stable content-free error and never falls back to another mode or provider.

Questions, prompt bodies, evidence, answers, and quotes are not logged by this use case. It adds no
persistence or telemetry containing those values. The fixture validates deterministic mechanics
only and establishes no answer-quality claim.

## Current boundary

There is intentionally no answer HTTP route, browser surface, live provider adapter, tool loop,
judge, or stored Q&A in EG-006. Local verification proves orchestration and citation trust-boundary
behavior; golden-set quality metrics and regression thresholds begin in EG-009.
