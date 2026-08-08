# ADR-0008: Separate local MCP stdio adapter

- Status: Accepted
- Date: 2026-08-08
- Story: EG-012

## Context

MCP is useful as an integration boundary but must not couple application logic to FastAPI or delay the core release.

## Decision

After the core release, expose structured search and ask tools from a separate local stdio executable using the shared application core. Reverify the current MCP protocol and Python SDK at story start. Protocol only on stdout; diagnostics on stderr.

## Consequences

MCP is cuttable from R3. No remote MCP transport or side-effecting tool is included.

## Verification

In-memory client contract tests and one subprocess/stdio test.
