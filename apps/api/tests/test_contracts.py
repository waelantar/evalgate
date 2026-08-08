"""Semantic checks for foundation and draft repository contracts."""

import json
import re
from pathlib import Path
from typing import cast

import yaml
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.config import Settings
from evalgate.entrypoints.http import create_app

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_foundation_openapi_references_are_strings() -> None:
    contract = yaml.safe_load(
        (REPOSITORY_ROOT / "contracts" / "openapi" / "foundation.yaml").read_text(encoding="utf-8")
    )

    live_schema = contract["paths"]["/health/live"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    ready_responses = contract["paths"]["/health/ready"]["get"]["responses"]

    assert live_schema == {"$ref": "#/components/schemas/HealthResponse"}
    assert set(ready_responses) == {"200", "503"}
    assert all(
        response["content"]["application/json"]["schema"]
        == {"$ref": "#/components/schemas/HealthResponse"}
        for response in ready_responses.values()
    )


def test_foundation_openapi_matches_the_running_application() -> None:
    contract = yaml.safe_load(
        (REPOSITORY_ROOT / "contracts" / "openapi" / "foundation.yaml").read_text(encoding="utf-8")
    )
    generated = create_app(
        settings=Settings(
            database_url=SecretStr("postgresql+psycopg://ignored:ignored@localhost/ignored")
        ),
        engine=cast(AsyncEngine, object()),
    ).openapi()

    assert generated["info"]["title"] == contract["info"]["title"]
    assert generated["info"]["version"] == contract["info"]["version"]

    for path in ("/health/live", "/health/ready"):
        expected_operation = contract["paths"][path]["get"]
        actual_operation = generated["paths"][path]["get"]
        assert actual_operation["operationId"] == expected_operation["operationId"]
        assert actual_operation["tags"] == expected_operation["tags"]
        assert set(actual_operation["responses"]) == set(expected_operation["responses"])
        for status in expected_operation["responses"]:
            actual_response = actual_operation["responses"][status]
            expected_response = expected_operation["responses"][status]
            assert actual_response["description"] == expected_response["description"]
            assert (
                actual_response["content"]["application/json"]["schema"]
                == expected_response["content"]["application/json"]["schema"]
            )

    expected_schema = contract["components"]["schemas"]["HealthResponse"]
    actual_schema = generated["components"]["schemas"]["HealthResponse"]
    assert actual_schema["additionalProperties"] is expected_schema["additionalProperties"]
    assert set(actual_schema["required"]) == set(expected_schema["required"])
    assert actual_schema["properties"]["service"]["const"] == "evalgate-api"
    assert actual_schema["properties"]["status"]["enum"] == [
        "alive",
        "ready",
        "not_ready",
    ]


def test_corpus_manifest_path_pattern_accepts_only_markdown_documents() -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "contracts" / "manifests" / "corpus.schema.json").read_text(
            encoding="utf-8"
        )
    )
    pattern = schema["$defs"]["document"]["properties"]["path"]["pattern"]

    assert re.fullmatch(pattern, "documents/runbooks/incident-01.md")
    assert not re.fullmatch(pattern, "documents/runbooks/incident-01xmd")
    assert not re.fullmatch(pattern, r"documents\runbooks\incident-01.md")
    assert not re.fullmatch(pattern, "../documents/incident-01.md")
