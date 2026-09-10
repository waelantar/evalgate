import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchEvaluationCases, fetchEvaluationRun, fetchEvaluationRuns } from './evaluationRuns'

afterEach(() => vi.unstubAllGlobals())

describe('evaluation results client', () => {
  it('validates list, detail, and case responses at runtime', async () => {
    const responses = [
      { items: [{ run_key: 'candidate', mode: 'retrieval', status: 'completed', code_sha: 'a', artifact_sha256: 'b' }], next_cursor: null },
      { run_key: 'candidate', mode: 'retrieval', status: 'completed', code_sha: 'a', artifact_sha256: 'b', versions: {}, environment: {}, metrics: { mrr: 0.8 }, limitations: ['bounded'], review: {}, comparison_run_key: null, metric_deltas: null },
      { items: [{ case_id: 'dev-01', split: 'development', question: 'Question?', answerable: true, status: 'failed', retrieved_evidence_ids: [], relevant_evidence_ids: ['e1'], metric_values: { retrieval_hit: 0 } }], next_cursor: null },
    ]
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve({ ok: true, json: () => Promise.resolve(responses.shift()) })))

    expect((await fetchEvaluationRuns()).items[0]?.run_key).toBe('candidate')
    expect((await fetchEvaluationRun('candidate', null)).metrics.mrr).toBe(0.8)
    expect((await fetchEvaluationCases('candidate', 'failed')).items[0]?.status).toBe('failed')
  })

  it('rejects malformed or unsuccessful responses without exposing server content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [{}], next_cursor: null }) }).mockResolvedValueOnce({ ok: false }))
    await expect(fetchEvaluationRuns()).rejects.toThrow('invalid response')
    await expect(fetchEvaluationRuns()).rejects.toThrow('results are unavailable')
  })
})
