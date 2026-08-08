#!/usr/bin/env sh
set -eu

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

uv run --python 3.13.15 --project apps/api --locked python scripts/check_publication.py
uv run --python 3.13.15 --project apps/api --locked python scripts/check_metadata.py
docker compose config --quiet

(
  cd apps/api
  uv run --python 3.13.15 --locked ruff format --check src tests
  uv run --python 3.13.15 --locked ruff check src tests
  uv run --python 3.13.15 --locked mypy src tests
  uv run --python 3.13.15 --locked pytest
)

(
  cd apps/web
  npm run lint
  npm run test
  npm run build
)
