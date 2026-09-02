export type EvaluationRun = Readonly<{ run_key: string; mode: string; status: string; code_sha: string; artifact_sha256: string }>
export type EvaluationRunPage = Readonly<{ items: EvaluationRun[]; next_cursor: string | null }>

export async function fetchEvaluationRuns(signal?: AbortSignal): Promise<EvaluationRunPage> {
  const response = await fetch('/api/v1/evaluation-runs', { headers: { Accept: 'application/json' }, signal })
  if (!response.ok) throw new Error('evaluation results are unavailable')
  return response.json() as Promise<EvaluationRunPage>
}
