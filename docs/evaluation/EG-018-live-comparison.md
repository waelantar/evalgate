# EG-018 Kubernetes live model comparison report

This report records the approved EG-018 OpenRouter evaluation of the pinned Kubernetes debug-cluster showcase. It is governed product evidence, not a public benchmark, provider endorsement, deployment claim, or universal model ranking.

## Executive conclusion

- EvalGate completed a comparable 18-case run for three models with the same corpus, index, dataset, retrieval limit, prompt policy, JSON schema, temperature, privacy posture, and one repetition per case.
- The original zero-cost failures for DeepSeek 0731 and GLM were caused by stale EvalGate `max_price` ceilings. Every selected provider cost more than the configured ceiling, so OpenRouter had no eligible route before inference.
- After correcting the reviewed ceilings, DeepSeek 0731 completed at 22.22% pass/citation recall and GLM completed at 16.67%. The base DeepSeek run was also 16.67%. These are weak results and do not support a production-quality claim.
- Hy3 and MiMo were valid diagnostic candidates but were not admitted to the full comparable set: Hy3 timed out on DeepInfra and was unavailable through Tencent under the required policy; MiMo returned malformed output on DeepInfra and was unavailable through Xiaomi.
- The useful result is the evaluation system itself: it exposes routing errors, timeouts, schema/citation failures, cost, and case evidence instead of turning infrastructure failures into misleading model scores.

## Controlled boundary

- Source: Kubernetes website `content/en/docs/tasks/debug/debug-cluster/` at commit `aa4e9e6dee49106155072a44ef997b91722243ec`, 11 Markdown files, CC BY 4.0.
- Dataset: `contracts/evaluation/kubernetes-debug-v1.json`, 18 reviewed EvalGate-authored cases.
- Index: `fe3b7d3e-727c-5973-b871-aaa6308bae6a`.
- Request: OpenRouter `/responses`, strict JSON schema, `temperature: 0`, reasoning omitted, `zdr: true`, `data_collection: deny`, `allow_fallbacks: false`, `require_parameters: true`, provider pinning for diagnosis, and model-specific price ceilings.
- Owner-approved expansion budget: USD 1.00; stop limit: USD 0.80.
- No browser secret, provider fallback, deployment, push, or merge was used.

## Comparable 18-case results

| Model | Provider route | Passed | Pass rate | Citation recall | Judge agreement | Evaluated by judge | Cost USD | Status summary |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `deepseek/deepseek-v4-flash` | approved price route | 3/18 | 16.67% | 16.67% | 28.57% | 14 | 0.001457442 | answered 11; insufficient support 3; malformed output 4 |
| `deepseek/deepseek-v4-flash-0731` | DeepInfra | 4/18 | 22.22% | 22.22% | 36.36% | 11 | 0.003003420 | answered 7; insufficient support 4; malformed output 1; unavailable 5; timeout 1 |
| `z-ai/glm-5.3-flash` | NextBit | 3/18 | 16.67% | 16.67% | 100.00% | 14 | 0.011564736 | answered 11; insufficient support 3; malformed output 4 |

The three rows are comparable at the EvalGate contract level, but provider availability still differs. DeepSeek 0731's five mid-run unavailable cases and one timeout remain failures; they are not removed from the denominator.

## Root-cause evidence

The first provider-pinned reruns recorded `provider_unavailable=18` and zero cost because their configured price ceilings were stale:

| Model | Old ceiling input/output per 1M | Selected current route price input/output per 1M | Result |
|---|---:|---:|---|
| DeepSeek 0731 | 0.0558 / 0.1767 | DeepInfra 0.06 / 0.18; Inceptron 0.08 / 0.20 | No provider eligible under the old ceiling |
| GLM 5.3 Flash | 0.075 / 0.25 | NextBit 0.18 / 0.60; Modal 0.45 / 1.50 | No provider eligible under the old ceiling |
| Hy3 | 0.105 / 0.435 | DeepInfra 0.14 / 0.58 | No provider eligible under the old ceiling |
| MiMo V2.5 | 0.119 / 0.238 | DeepInfra 0.133 / 0.266 | No provider eligible under the old ceiling |

EvalGate now retains hard ceilings at the reviewed route maxima: DeepSeek 0731 0.08/0.20, GLM 0.45/1.50, Hy3 0.14/0.58, and MiMo 0.14/0.28. The overall budget and lower stop limit remain the final spend controls.

## Additional candidate diagnostics

| Model | Provider | Outcome | Cost USD | Decision |
|---|---|---|---:|---|
| Hy3 | DeepInfra | One case reached inference but timed out | 0.000000000 | Excluded from full comparison |
| Hy3 | Tencent | Provider unavailable under required policy | 0.000000000 | Excluded from full comparison |
| MiMo V2.5 | DeepInfra | One paid response violated the answer/citation contract | 0.000576023 | Excluded from full comparison |
| MiMo V2.5 | Xiaomi | Provider unavailable under required policy | 0.000000000 | Excluded from full comparison |

These are provider/contract diagnostics, not scored model-quality rows. EvalGate does not weaken privacy, fallback, or structured-output rules to manufacture a result.

## Spend reconciliation

- Initial comparison and first rerun: USD 0.003757232.
- Repaired DeepSeek/GLM smoke checks: USD 0.001071948.
- Hy3/MiMo diagnostic smokes: USD 0.000576023.
- Repaired full DeepSeek 0731 and GLM runs: USD 0.014568156.
- Total artifact-reported EG-018 spend: USD 0.019973359.
- Remaining margin to the USD 0.80 stop: USD 0.780026641.

## Interpretation

1. The runner can evaluate multiple models; the earlier apparent inability was an EvalGate routing-policy defect.
2. None of the three comparable runs is strong enough for a production-quality or model-winner claim.
3. GLM's 100% judge agreement is not a quality score. It means the advisory judge agreed on the 14 outputs it could evaluate; only 3 of 18 repetitions passed the primary label.
4. DeepSeek 0731 has the highest observed pass rate in this one small run, but also the worst availability profile. The evidence does not justify calling it best.
5. The next evaluation change should classify retrieval misses separately from generation, citation, provider, and judge failures before changing prompts or models.

## Repaired artifact hashes

- `artifacts/eg-018-expansion/kubernetes-live-deepseek-v4-flash-0731-deepinfra-fixed.json`: `45c43462acb1220dc2712cffed63dcbd2982e32b7d1f0337d447676094d75b7d`
- `artifacts/eg-018-expansion/kubernetes-live-glm-5-3-flash-nextbit-fixed.json`: `4820db4fd56f414f5ae0380bf388cb6928c4d48a9c0ea3c7dca08e19a47b7c25`
- `artifacts/eg-018-expansion/smoke-deepseek-0731-deepinfra.json`: `7c665a8f4f4a66399d8183cda34996817e36ce0a1735b969a46da874f7f94df9`
- `artifacts/eg-018-expansion/smoke-glm-5-3-flash-nextbit.json`: `55a25483bb7e78e0f9c929d4cb1a733553baec7924b8e2496258f21605503549`
- `artifacts/eg-018-expansion/smoke-hy3-deepinfra.json`: `3331f95e2a0591d896112c3377c950583dc24798b621c5489fb88520f1a9d4de`
- `artifacts/eg-018-expansion/smoke-hy3-tencent.json`: `cab3dc5c70254fb9c51150a91aabe6c8092d9b37e8fb6bfba2f6878bb693b85b`
- `artifacts/eg-018-expansion/smoke-mimo-v2-5-deepinfra.json`: `5bf1e3f2701e4ce3acad3e258837a9b52ee1167a334f34579ab4827d67378c77`
- `artifacts/eg-018-expansion/smoke-mimo-v2-5-xiaomi.json`: `4f418c9d0326d0053dfc02d35936b6d27d839a5ce2417ace50707485aa2d161e`

The ignored local artifacts are integrity-bound by these hashes and the tracked review records. The tracked report contains no prompt bodies, duplicated corpus text, API key, or private user data.
