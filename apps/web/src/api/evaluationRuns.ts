export type EvaluationRun = Readonly<{
  run_key: string
  mode: string
  status: string
  code_sha: string
  artifact_sha256: string
}>

export type EvaluationRunPage = Readonly<{ items: EvaluationRun[]; next_cursor: string | null }>

export type EvaluationRunDetail = EvaluationRun & Readonly<{
  versions: Readonly<Record<string, unknown>>
  environment: Readonly<Record<string, unknown>>
  metrics: Readonly<Record<string, number>>
  limitations: readonly string[]
  review: Readonly<Record<string, unknown>>
  comparison_run_key: string | null
  metric_deltas: Readonly<Record<string, number>> | null
}>

export type EvaluationCase = Readonly<{
  case_id: string
  split: string
  question: string
  answerable: boolean
  status: string
  retrieved_evidence_ids: readonly string[]
  relevant_evidence_ids: readonly string[]
  metric_values: Readonly<Record<string, number>>
}>

export type EvaluationCasePage = Readonly<{
  items: EvaluationCase[]
  next_cursor: string | null
}>

export type CaseStatus = 'passed' | 'failed'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringField(value: Record<string, unknown>, key: string): string {
  const field = value[key]
  if (typeof field !== 'string') throw new Error('evaluation results returned an invalid response')
  return field
}

function nullableString(value: unknown): string | null {
  if (value === null || typeof value === 'string') return value
  throw new Error('evaluation results returned an invalid response')
}

function numberRecord(value: unknown): Record<string, number> {
  if (!isRecord(value) || Object.values(value).some((item) => typeof item !== 'number')) {
    throw new Error('evaluation results returned an invalid response')
  }
  return value as Record<string, number>
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    throw new Error('evaluation results returned an invalid response')
  }
  const items: string[] = []
  for (const item of value as unknown[]) {
    if (typeof item !== 'string') throw new Error('evaluation results returned an invalid response')
    items.push(item)
  }
  return items
}

function parseRun(value: unknown): EvaluationRun {
  if (!isRecord(value)) throw new Error('evaluation results returned an invalid response')
  return {
    run_key: stringField(value, 'run_key'),
    mode: stringField(value, 'mode'),
    status: stringField(value, 'status'),
    code_sha: stringField(value, 'code_sha'),
    artifact_sha256: stringField(value, 'artifact_sha256'),
  }
}

function parseRunPage(value: unknown): EvaluationRunPage {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new Error('evaluation results returned an invalid response')
  }
  return { items: value.items.map(parseRun), next_cursor: nullableString(value.next_cursor) }
}

function parseRunDetail(value: unknown): EvaluationRunDetail {
  if (!isRecord(value)) throw new Error('evaluation results returned an invalid response')
  const run = parseRun(value)
  if (!isRecord(value.versions) || !isRecord(value.environment) || !isRecord(value.review)) {
    throw new Error('evaluation results returned an invalid response')
  }
  return {
    ...run,
    versions: value.versions,
    environment: value.environment,
    metrics: numberRecord(value.metrics),
    limitations: stringArray(value.limitations),
    review: value.review,
    comparison_run_key: nullableString(value.comparison_run_key),
    metric_deltas: value.metric_deltas === null ? null : numberRecord(value.metric_deltas),
  }
}

function parseCase(value: unknown): EvaluationCase {
  if (!isRecord(value) || typeof value.answerable !== 'boolean') {
    throw new Error('evaluation results returned an invalid response')
  }
  return {
    case_id: stringField(value, 'case_id'),
    split: stringField(value, 'split'),
    question: stringField(value, 'question'),
    answerable: value.answerable,
    status: stringField(value, 'status'),
    retrieved_evidence_ids: stringArray(value.retrieved_evidence_ids),
    relevant_evidence_ids: stringArray(value.relevant_evidence_ids),
    metric_values: numberRecord(value.metric_values),
  }
}

function parseCasePage(value: unknown): EvaluationCasePage {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new Error('evaluation results returned an invalid response')
  }
  return { items: value.items.map(parseCase), next_cursor: nullableString(value.next_cursor) }
}

async function requestJson(path: string, signal?: AbortSignal): Promise<unknown> {
  const init: RequestInit = { headers: { Accept: 'application/json' } }
  if (signal !== undefined) init.signal = signal
  const response = await fetch(path, init)
  if (!response.ok) throw new Error('evaluation results are unavailable')
  return response.json() as Promise<unknown>
}

export async function fetchEvaluationRuns(signal?: AbortSignal): Promise<EvaluationRunPage> {
  return parseRunPage(await requestJson('/api/v1/evaluation-runs?limit=50', signal))
}

export async function fetchEvaluationRun(
  runKey: string,
  compareTo: string | null,
  signal?: AbortSignal,
): Promise<EvaluationRunDetail> {
  const query = compareTo === null ? '' : `?compare_to=${encodeURIComponent(compareTo)}`
  return parseRunDetail(
    await requestJson(`/api/v1/evaluation-runs/${encodeURIComponent(runKey)}${query}`, signal),
  )
}

export async function fetchEvaluationCases(
  runKey: string,
  status: CaseStatus | null,
  signal?: AbortSignal,
): Promise<EvaluationCasePage> {
  const query = new URLSearchParams({ limit: '50' })
  if (status !== null) query.set('status', status)
  return parseCasePage(
    await requestJson(
      `/api/v1/evaluation-runs/${encodeURIComponent(runKey)}/cases?${query.toString()}`,
      signal,
    ),
  )
}
