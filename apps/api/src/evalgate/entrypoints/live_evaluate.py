"""Run the protected governed live-generation evaluation suite."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine

from evalgate import __version__
from evalgate.adapters.openrouter_generation import (
    OPENROUTER_MODEL,
    OpenRouterGenerationAdapter,
    OpenRouterGenerationConfig,
    OpenRouterGenerationError,
)
from evalgate.application.answer import (
    GROUNDED_ANSWER_V1,
    AnswerError,
    AnswerErrorCode,
    AnswerPolicy,
    AnswerRequest,
    answer_policy_content_sha256,
    complete_prepared_answer,
    prepare_answer,
)
from evalgate.application.ports import GenerationPort
from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    LiveProvider,
)
from evalgate.application.runtime_security import environment_policy
from evalgate.config import Settings
from evalgate.domain.answer import AnswerMode, AnswerResult, AnswerStatus
from evalgate.domain.providers import (
    GenerationInput,
    GenerationOutput,
    GenerationUsage,
    ProviderIdentity,
)
from evalgate.entrypoints.retrieval_runtime import build_reference_retrieval, database_event_loop

_JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision", "reason_code"],
    "properties": {
        "decision": {"enum": ["pass", "fail"]},
        "reason_code": {
            "enum": [
                "supported_answer",
                "correct_insufficient_support",
                "wrong_answerability",
                "missing_relevant_citation",
                "unsupported_claim",
            ]
        },
    },
}

_ANSWER_FAILURE_STATUS: dict[AnswerErrorCode, str] = {
    AnswerErrorCode.PROVIDER_UNAVAILABLE: "provider_unavailable",
    AnswerErrorCode.PROVIDER_TIMEOUT: "provider_timeout",
    AnswerErrorCode.PROVIDER_MALFORMED_OUTPUT: "malformed_output",
    AnswerErrorCode.CITATION_MISSING: "citation_missing",
    AnswerErrorCode.CITATION_SPOOFED: "citation_spoofed",
    AnswerErrorCode.CONTEXT_INVALID: "context_invalid",
    AnswerErrorCode.EVIDENCE_INVALID: "evidence_invalid",
}

_ANSWER_FAILURE_REASON: dict[AnswerErrorCode, str] = {
    AnswerErrorCode.PROVIDER_UNAVAILABLE: "provider_unavailable",
    AnswerErrorCode.PROVIDER_TIMEOUT: "provider_timeout",
    AnswerErrorCode.PROVIDER_MALFORMED_OUTPUT: "malformed_output",
    AnswerErrorCode.CITATION_MISSING: "malformed_output",
    AnswerErrorCode.CITATION_SPOOFED: "citation_invalid",
    AnswerErrorCode.CONTEXT_INVALID: "context_invalid",
    AnswerErrorCode.EVIDENCE_INVALID: "citation_invalid",
}


@dataclass(frozen=True, slots=True)
class _ReviewedCase:
    case_id: str
    split: str
    question: str
    answerability: str
    relevant_evidence_ids: tuple[str, ...]
    supported_claims: tuple[str, ...]


class _RecordingGeneration:
    def __init__(self, inner: GenerationPort) -> None:
        self._inner = inner
        self.last_output: GenerationOutput | None = None

    @property
    def identity(self) -> ProviderIdentity:
        return self._inner.identity

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        self.last_output = await self._inner.generate(request)
        return self.last_output


def _load_dataset(path: Path) -> tuple[str, tuple[_ReviewedCase, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0" or not isinstance(raw.get("cases"), list):
        raise ValueError("live evaluation dataset has an unsupported schema")
    cases: list[_ReviewedCase] = []
    for value in raw["cases"]:
        if value.get("review_state") != "reviewed":
            raise ValueError("live evaluation requires reviewed cases")
        cases.append(
            _ReviewedCase(
                case_id=value["case_id"],
                split=value["split"],
                question=value["question"],
                answerability=value["answerability"],
                relevant_evidence_ids=tuple(value["relevant_evidence_ids"]),
                supported_claims=tuple(value["supported_claims"]),
            )
        )
    return raw["dataset_version"], tuple(cases)


def _live_answer_policy(settings: Settings) -> AnswerPolicy:
    candidate = replace(
        GROUNDED_ANSWER_V1,
        content_sha256="0" * 64,
        provider_timeout_seconds=settings.openrouter_timeout_seconds,
    )
    return replace(candidate, content_sha256=answer_policy_content_sha256(candidate))


def _usage(value: GenerationUsage | None) -> dict[str, float]:
    if value is None:
        return {"input_tokens": 0.0, "output_tokens": 0.0, "total_tokens": 0.0, "cost_usd": 0.0}
    return {
        "input_tokens": float(value.input_tokens),
        "output_tokens": float(value.output_tokens),
        "total_tokens": float(value.total_tokens),
        "cost_usd": value.cost_usd,
    }


def _human_pass(case: _ReviewedCase, result: AnswerResult) -> bool:
    cited = {str(item.evidence_id) for item in result.citations}
    relevant = set(case.relevant_evidence_ids)
    if case.answerability == "unanswerable":
        return result.status is AnswerStatus.INSUFFICIENT_SUPPORT and not cited
    return result.status is AnswerStatus.ANSWERED and bool(cited & relevant)


def _citation_recall(case: _ReviewedCase, result: AnswerResult) -> float:
    if not case.relevant_evidence_ids:
        return 1.0 if not result.citations else 0.0
    cited = {str(item.evidence_id) for item in result.citations}
    return len(cited & set(case.relevant_evidence_ids)) / len(case.relevant_evidence_ids)


def _retrieved_evidence_ids(result: AnswerResult) -> list[str]:
    return [str(item.evidence.evidence_id) for item in result.evidence]


def _prepared_evidence_ids(prepared_evidence: Any) -> list[str]:
    return [str(item.evidence.evidence_id) for item in prepared_evidence]


def _answer_failure_status(error: AnswerError) -> str:
    return _ANSWER_FAILURE_STATUS.get(error.code, "provider_unavailable")


def _answer_failure_reason(error: AnswerError) -> str:
    return _ANSWER_FAILURE_REASON.get(error.code, "provider_unavailable")


def _judge_prompt(case: _ReviewedCase, result: AnswerResult) -> str:
    payload = {
        "task": "Judge whether the generated answer should pass the reviewed EvalGate case.",
        "rules": [
            "Use only the reviewed labels, generated answer, and selected evidence supplied here.",
            "Pass answerable cases only when the answer is supported by cited relevant evidence.",
            "Pass unanswerable cases only when the result is insufficient_support with no "
            "citations.",
            "Return only the requested JSON object.",
        ],
        "reviewed_case": {
            "case_id": case.case_id,
            "answerability": case.answerability,
            "relevant_evidence_ids": list(case.relevant_evidence_ids),
            "supported_claims": list(case.supported_claims),
        },
        "generated": {
            "status": result.status.value,
            "answer": result.answer,
            "citations": [
                {
                    "claim": item.claim,
                    "evidence_id": str(item.evidence_id),
                    "quote": item.quote,
                }
                for item in result.citations
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


async def build_live_generation_artifact(
    *,
    dataset_path: Path,
    index_version: UUID,
    settings: Settings,
    generation: GenerationPort,
    judge: GenerationPort,
    repetitions: int,
    max_cases: int | None,
) -> dict[str, Any]:
    """Build one governed live-generation artifact without persisting prompts or completions."""

    if not environment_policy(settings.environment).allow_evaluation:
        raise ValueError("live generation evaluation is unavailable in this environment")
    if settings.embedding_mode is not EmbeddingMode.REFERENCE:
        raise ValueError("live generation evaluation requires reference retrieval")
    if settings.generation_mode is not GenerationMode.LIVE:
        raise ValueError("live generation evaluation requires live generation mode")
    configuration = settings.provider_configuration()
    if configuration.live_provider is not LiveProvider.OPENROUTER:
        raise ValueError("live generation evaluation requires the approved OpenRouter provider")
    if repetitions < 1:
        raise ValueError("live generation evaluation requires at least one repetition")

    dataset_version, cases = _load_dataset(dataset_path)
    selected_cases = cases if max_cases is None else cases[:max_cases]
    if not selected_cases:
        raise ValueError("live generation evaluation selected no cases")
    policy = _live_answer_policy(settings)

    engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    started_at = datetime.now(UTC)
    total_cost = 0.0
    try:
        repository, embedding = build_reference_retrieval(settings=settings, engine=engine)
        artifact_cases: list[dict[str, Any]] = []
        human_passes: list[float] = []
        citation_recalls: list[float] = []
        judge_agreements: list[float] = []
        resolved_index = None
        for case in selected_cases:
            case_number = len(artifact_cases) + 1
            case_repetitions: list[dict[str, Any]] = []
            for repetition in range(1, repetitions + 1):
                prepared = await prepare_answer(
                    request=AnswerRequest(
                        question=case.question,
                        index_version=index_version,
                        mode=AnswerMode.LIVE,
                        retrieval_limit=5,
                    ),
                    embedding=embedding,
                    repository=repository,
                    policy=policy,
                )
                resolved_index = prepared.index
                recorder = _RecordingGeneration(generation)
                try:
                    result = await complete_prepared_answer(prepared=prepared, generation=recorder)
                except AnswerError as error:
                    answer_usage = _usage(
                        recorder.last_output.usage if recorder.last_output else None
                    )
                    total_cost += answer_usage["cost_usd"]
                    if total_cost > settings.live_eval_stop_usd:
                        raise ValueError(
                            "live generation evaluation exceeded the approved stop limit"
                        ) from error
                    human_passes.append(0.0)
                    citation_recalls.append(0.0)
                    case_repetitions.append(
                        {
                            "repetition": repetition,
                            "answer_status": _answer_failure_status(error),
                            "retrieved_evidence_ids": _prepared_evidence_ids(prepared.evidence),
                            "citation_evidence_ids": [],
                            "generation_usage": answer_usage,
                            "judge_decision": "fail",
                            "judge_reason_code": _answer_failure_reason(error),
                            "judge_usage": _usage(None),
                            "human_label": "fail",
                            "passed": False,
                        }
                    )
                    print(
                        "completed live evaluation repetition "
                        f"{case_number}/{len(selected_cases)}:{repetition}/{repetitions}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue

                answer_usage = _usage(recorder.last_output.usage if recorder.last_output else None)
                total_cost += answer_usage["cost_usd"]
                if total_cost > settings.live_eval_stop_usd:
                    raise ValueError("live generation evaluation exceeded the approved stop limit")
                human_pass = _human_pass(case, result)
                recall = _citation_recall(case, result)
                judge_recorder = _RecordingGeneration(judge)
                try:
                    judge_output = await asyncio.wait_for(
                        judge_recorder.generate(GenerationInput(_judge_prompt(case, result))),
                        timeout=settings.openrouter_timeout_seconds,
                    )
                    judge_usage = _usage(
                        judge_recorder.last_output.usage if judge_recorder.last_output else None
                    )
                    total_cost += judge_usage["cost_usd"]
                    if total_cost > settings.live_eval_stop_usd:
                        raise ValueError(
                            "live generation evaluation exceeded the approved stop limit"
                        )
                    judge_value = json.loads(judge_output.text)
                    judge_pass = judge_value["decision"] == "pass"
                    judge_decision = judge_value["decision"]
                    judge_reason_code = judge_value["reason_code"]
                    judge_agreements.append(1.0 if judge_pass == human_pass else 0.0)
                except (
                    TimeoutError,
                    OpenRouterGenerationError,
                    KeyError,
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
                ):
                    judge_usage = _usage(
                        judge_recorder.last_output.usage if judge_recorder.last_output else None
                    )
                    judge_decision = "fail"
                    judge_reason_code = "judge_invalid"
                human_passes.append(1.0 if human_pass else 0.0)
                citation_recalls.append(recall)
                case_repetitions.append(
                    {
                        "repetition": repetition,
                        "answer_status": result.status.value,
                        "retrieved_evidence_ids": _retrieved_evidence_ids(result),
                        "citation_evidence_ids": [
                            str(item.evidence_id) for item in result.citations
                        ],
                        "generation_usage": answer_usage,
                        "judge_decision": judge_decision,
                        "judge_reason_code": judge_reason_code,
                        "judge_usage": judge_usage,
                        "human_label": "pass" if human_pass else "fail",
                        "passed": human_pass,
                    }
                )
                print(
                    "completed live evaluation repetition "
                    f"{case_number}/{len(selected_cases)}:{repetition}/{repetitions}",
                    file=sys.stderr,
                    flush=True,
                )
            artifact_cases.append(
                {
                    "case_id": case.case_id,
                    "split": case.split,
                    "answerability": case.answerability,
                    "relevant_evidence_ids": list(case.relevant_evidence_ids),
                    "supported_claims": list(case.supported_claims),
                    "repetitions": case_repetitions,
                }
            )
        code_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if resolved_index is None:
            raise ValueError("live generation evaluation did not resolve an index")
        dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        prompt_sha256 = answer_policy_content_sha256(policy)
        finished_at = datetime.now(UTC)
        repetition_count = len(human_passes)
        return {
            "schema_version": "1.0",
            "run": {
                "run_key": f"golden-{dataset_version}-openrouter-deepseek-v4-flash",
                "mode": "generation",
                "status": "completed",
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
            },
            "versions": {
                "code_sha": code_sha,
                "corpus_manifest_sha256": resolved_index.corpus_manifest_sha256,
                "index_key": resolved_index.index_key,
                "dataset_manifest_sha256": dataset_sha256,
                "policy_version": policy.version,
                "prompt_sha256": prompt_sha256,
                "generation_model": OPENROUTER_MODEL,
                "judge_model": OPENROUTER_MODEL,
            },
            "environment": {
                "os": platform.system(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "postgres_image_digest": (
                    "sha256:9d2e61c7352b9e9f4798df5fd9a498f043f4cda1cdacc707de3d198650f4321e"
                ),
                "numeric_tolerance": 1e-9,
            },
            "metrics": {
                "case_count": float(len(selected_cases)),
                "repetition_count": float(repetition_count),
                "human_pass_rate": sum(human_passes) / repetition_count,
                "citation_recall": sum(citation_recalls) / repetition_count,
                "human_judge_agreement": (
                    sum(judge_agreements) / len(judge_agreements) if judge_agreements else 0.0
                ),
                "judge_evaluated_count": float(len(judge_agreements)),
                "total_cost_usd": total_cost,
                "approved_budget_usd": settings.live_eval_budget_usd,
                "stop_limit_usd": settings.live_eval_stop_usd,
            },
            "cases": artifact_cases,
            "limitations": [
                "Live generation used one approved OpenRouter model through a protected local or "
                "manual workflow; ordinary pull-request CI remains secret-free.",
                "The same model produced answers and advisory judge labels, so judge agreement is "
                "calibration evidence, not an automatic release blocker.",
                "The artifact stores bounded IDs, labels, metrics, usage, cost, and limitations; "
                "it does not store prompts, raw completions, provider secrets, or corpus text.",
            ],
        }
    finally:
        await engine.dispose()


def _render_markdown(artifact: dict[str, Any]) -> str:
    run = artifact["run"]
    metrics = artifact["metrics"]
    versions = artifact["versions"]
    lines = [
        "# EvalGate governed live-generation evaluation",
        "",
        f"- Run: `{run['run_key']}`",
        f"- Mode: `{run['mode']}`",
        f"- Generation model: `{versions['generation_model']}`",
        f"- Judge model: `{versions['judge_model']}`",
        f"- Total cost: `${metrics['total_cost_usd']:.6f}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in metrics.items())
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in artifact["limitations"])
    return "\n".join(lines) + "\n"


def _build_openrouter_adapters(settings: Settings) -> tuple[GenerationPort, GenerationPort]:
    if settings.openrouter_api_key is None:
        raise ValueError("EVALGATE_OPENROUTER_API_KEY is required")
    base_config = OpenRouterGenerationConfig(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        base_url=settings.openrouter_base_url,
        timeout_seconds=settings.openrouter_timeout_seconds,
        budget_usd=settings.live_eval_budget_usd,
        stop_usd=settings.live_eval_stop_usd,
    )
    judge_config = OpenRouterGenerationConfig(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        base_url=settings.openrouter_base_url,
        timeout_seconds=settings.openrouter_timeout_seconds,
        budget_usd=settings.live_eval_budget_usd,
        stop_usd=settings.live_eval_stop_usd,
        max_output_tokens=300,
        response_schema_name="evalgate_live_judge",
        response_schema=_JUDGE_SCHEMA,
    )
    return OpenRouterGenerationAdapter(base_config), OpenRouterGenerationAdapter(judge_config)


def main() -> None:
    root = Path(__file__).resolve().parents[5]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=root / "contracts/evaluation/golden-v1.json"
    )
    parser.add_argument("--index-version", required=True, type=UUID)
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation-live.json"))
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()
    settings = Settings()
    generation, judge = _build_openrouter_adapters(settings)
    artifact = asyncio.run(
        build_live_generation_artifact(
            dataset_path=args.dataset,
            index_version=args.index_version,
            settings=settings,
            generation=generation,
            judge=judge,
            repetitions=args.repetitions,
            max_cases=args.max_cases,
        ),
        loop_factory=database_event_loop,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(_render_markdown(artifact), encoding="utf-8")
    print(f"wrote {args.output} for EvalGate {__version__}")


if __name__ == "__main__":
    main()
