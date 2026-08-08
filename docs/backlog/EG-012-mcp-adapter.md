# EG-012: Separate MCP stdio adapter

- Status: Planned; cuttable until R3 is accepted
- Branch: `feat/eg-012-mcp-adapter`
- Depends on: EG-014 accepted and merged to `main`
- Release: R4
- Blueprint requirements: G-08, FR-10, ADR-0008

## Outcome

A local MCP host can call structured search and ask tools through a separate stdio executable that shares application use cases but not FastAPI lifecycle state.

## Scope

- Reverify current official MCP protocol and Python SDK; record/pin selected versions.
- Freeze JSON input/output schemas for `search_corpus` and `ask_corpus` aligned with HTTP/core types; inputs select `index_version` and results report its source-corpus version.
- Separate executable/process, explicit local configuration, bounded arguments/results, stderr-only diagnostics.
- In-memory client contract tests and one subprocess/stdio integration test.

## Non-goals

- Remote MCP transport, FastAPI MCP route, provider credentials from tool arguments, streaming requirement, resources/prompts beyond demonstrated need, side-effecting tools, or agent loop.

## Acceptance evidence

- [ ] Tool schemas and results agree with the application core, select an index version, report the source corpus, and reject unknown/oversized input.
- [ ] Stdout contains protocol only; errors/logs use stderr without content leakage.
- [ ] In-memory and real stdio client tests pass on declared platforms.
- [ ] Removing the MCP package/process does not affect HTTP or core tests.

## Required tests and review

- Run JSON-schema compatibility, unknown/oversized input, application-port contract, in-memory client, real subprocess/stdio, stdout-purity, stderr-redaction, and package-removal boundary tests; review current official protocol/SDK evidence.

## Expected file ownership

- Versioned MCP tool schemas, separate stdio entrypoint/adapter and configuration, MCP client/subprocess tests, dependency pins, ADR-0008 update, and local-use documentation.

## Stop conditions

- Official protocol/SDK changed materially, remote transport is required, or implementation would couple to FastAPI or delay R3.

## Copy-paste coding-agent brief

> Work only on EG-012 on branch `feat/eg-012-mcp-adapter`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0008, current official MCP Python documentation, and this story. Confirm EG-014 is accepted and merged to clean `main`. Reverify/pin the protocol/SDK, freeze bounded tool schemas that select `index_version` and report source-corpus identity, and implement a separate local stdio adapter using existing application ports with protocol-only stdout and thorough client tests. Do not add remote transport, FastAPI coupling, side-effecting tools, provider arguments, or an agent loop. Do not merge, push, deploy, or spend. Finish with process/schema/data-flow explanation, files, exact tests, version evidence, limitations, and suggested commit message.
