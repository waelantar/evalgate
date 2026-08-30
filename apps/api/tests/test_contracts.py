"""Semantic checks for foundation and draft repository contracts."""

import json
import re
from pathlib import Path
from typing import cast

import yaml
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.application.answer import (
    GROUNDED_ANSWER_V1,
    OUTPUT_SCHEMA,
    SYSTEM_PROMPT,
    answer_policy_content_sha256,
)
from evalgate.application.search import (
    DEFAULT_RESULT_LIMIT,
    MAX_QUERY_CODE_POINTS,
    MAX_QUERY_TOKENS,
    MAX_RESULT_LIMIT,
    MIN_RESULT_LIMIT,
)
from evalgate.config import Settings
from evalgate.domain.search import HYBRID_RRF_V1
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

    assert generated == contract


def test_hybrid_retrieval_contract_matches_the_domain_policy() -> None:
    contract = json.loads(
        (REPOSITORY_ROOT / "contracts" / "retrieval" / "hybrid-rrf-v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert contract == {
        "schema_version": "1.0",
        "policy_id": HYBRID_RRF_V1.policy_id,
        "query": {
            "maximum_code_points": MAX_QUERY_CODE_POINTS,
            "maximum_tokens": MAX_QUERY_TOKENS,
            "normalization": "NFC; CRLF/CR to LF; trim outer Unicode whitespace",
            "lexical_parser": "plainto_tsquery",
            "lexical_regconfig": "pg_catalog.simple",
            "lexical_config_sha256": HYBRID_RRF_V1.lexical_config_sha256,
        },
        "result_limit": {
            "default": DEFAULT_RESULT_LIMIT,
            "minimum": MIN_RESULT_LIMIT,
            "maximum": MAX_RESULT_LIMIT,
        },
        "components": {
            "lexical": {
                "candidate_depth": HYBRID_RRF_V1.lexical_candidate_depth,
                "score": "ts_rank_cd descending",
                "tie_break": "evidence UUID ascending",
            },
            "vector": {
                "candidate_depth": HYBRID_RRF_V1.vector_candidate_depth,
                "score": "exact cosine distance ascending",
                "tie_break": "evidence UUID ascending",
            },
        },
        "fusion": {
            "algorithm": "reciprocal-rank-fusion",
            "rank_origin": 1,
            "constant": HYBRID_RRF_V1.rrf_constant,
            "missing_component_contribution": 0,
            "formula": "sum(1 / (60 + component_rank)) for each present component",
            "order": "RRF score descending, then evidence UUID ascending",
        },
    }


def test_grounded_answer_prompt_contract_matches_the_application_policy() -> None:
    contract = json.loads(
        (REPOSITORY_ROOT / "contracts" / "prompts" / "grounded-answer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    policy = GROUNDED_ANSWER_V1

    assert contract == {
        "schema_version": "1.0",
        "policy_id": policy.policy_id,
        "version": policy.version,
        "content_sha256": policy.content_sha256,
        "system_prompt": SYSTEM_PROMPT,
        "budgets": {
            "maximum_question_code_points": policy.maximum_question_code_points,
            "maximum_question_tokens": policy.maximum_question_tokens,
            "maximum_retrieval_limit": policy.maximum_retrieval_limit,
            "maximum_evidence_context_code_points": policy.maximum_evidence_context_code_points,
            "maximum_evidence_context_tokens": policy.maximum_evidence_context_tokens,
            "maximum_generation_output_code_points": policy.maximum_generation_output_code_points,
            "maximum_answer_code_points": policy.maximum_answer_code_points,
            "maximum_citation_associations": policy.maximum_citation_associations,
            "maximum_evidence_ids_per_association": policy.maximum_evidence_ids_per_association,
            "maximum_quote_code_points": policy.maximum_quote_code_points,
            "provider_timeout_seconds": policy.provider_timeout_seconds,
        },
        "output_schema": OUTPUT_SCHEMA,
    }
    assert answer_policy_content_sha256(policy) == policy.content_sha256


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
