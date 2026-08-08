# Security Policy

## Supported versions

Until the first tagged release, only the `main` branch receives security fixes. Supported release lines will be listed here once they exist.

## Reporting a vulnerability

Use the repository host's private security-advisory feature. Do not open a public issue for a suspected credential leak, remote-code-execution path, public cost-abuse path, or exploitable data exposure.

Include the affected commit or version, reproduction steps, impact, and any suggested mitigation. Do not include real credentials or personal/confidential data in the report.

## Current security posture

The repository is pre-production. It has no approved public deployment and no authorized live-provider configuration. See the threat model and release gates in `BLUEPRINT.md`. A local development service must not be exposed to the public internet.
