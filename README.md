# EvalGate

EvalGate helps AI application teams detect retrieval, grounding, and citation regressions before release.

The repository currently contains the approved production blueprint and the reproducible engineering foundation. Product capabilities remain planned; the status table below is the source of truth.

| Capability | Status |
|---|---|
| Production blueprint | Approved |
| Repository/tooling foundation | Static and code checks pass; PostgreSQL runtime and remote CI pending |
| Corpus and ingestion | Planned |
| Hybrid retrieval and cited answer | Planned |
| Evaluation gate and results UI | Planned |
| MCP adapter | Deferred until the core release |
| Public deployment | Not selected or deployed |

Start with [BLUEPRINT.md](BLUEPRINT.md). The detailed implementation queue is in [docs/backlog](docs/backlog/README.md), and architectural changes are recorded in [docs/adr](docs/adr/README.md).

Future work follows the [one-story branch and manual-merge workflow](docs/WORKFLOW.md). The coding agent prepares and explains a story branch; the repository owner reviews and merges it manually.

## Prerequisites

- Git
- Docker with Compose v2
- Python 3.13.15 and [uv 0.12.3](https://docs.astral.sh/uv/)
- Node.js 24.19.0 LTS

## Local setup

PowerShell:

```powershell
./scripts/bootstrap.ps1
./scripts/check.ps1
```

POSIX shell:

```sh
./scripts/bootstrap.sh
./scripts/check.sh
```

Then run the services in separate terminals:

```powershell
uv run --python 3.13.15 --project apps/api --locked evalgate-api
npm --prefix apps/web run dev
```

- Web: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Liveness: <http://127.0.0.1:8000/health/live>

Copy `.env.example` to `.env` only when overriding local defaults. No generation/provider configuration or external provider call exists in the foundation; EG-002 owns that boundary.

## Repository map

```text
apps/api/           Python application core and API adapters
apps/web/           React foundation; inspection interface begins in EG-008
contracts/          Versioned machine-readable contracts
data/               Governed corpus, golden set, and manifests
docs/adr/           Architecture decision records
docs/backlog/       Story contracts and implementation briefs
docs/runbooks/      Operational procedures
scripts/            Reproducible developer and publication checks
```

## License

Code is available under the MIT License. Corpus content will not be added until its separate data-license gate is complete.
