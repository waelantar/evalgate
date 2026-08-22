#!/usr/bin/env sh
set -eu

for command_name in docker uv node npm; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Required command '$command_name' is not available on PATH." >&2
    exit 1
  }
done

node_version="$(node --version)"
if [ "$node_version" != "v24.19.0" ]; then
  echo "Node.js 24.19.0 is required; found $node_version." >&2
  exit 1
fi
uv_version_output="$(uv --version)"
uv_version="${uv_version_output#uv }"
uv_version="${uv_version%% *}"
if [ "$uv_version" != "0.12.3" ]; then
  echo "uv 0.12.3 is required; found $uv_version_output." >&2
  exit 1
fi

docker compose config --quiet
docker compose up -d --wait db

(cd apps/api && uv sync --python 3.13.15 --locked && uv run --python 3.13.15 --locked evalgate-db seed-empty)
(cd apps/web && npm ci)

echo "EvalGate foundation is ready. Start the API and web app using README.md."
