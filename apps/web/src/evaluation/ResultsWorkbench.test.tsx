import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResultsWorkbench } from './ResultsWorkbench'

const api = vi.hoisted(() => ({
  list: vi.fn(),
  detail: vi.fn(),
  cases: vi.fn(),
}))

vi.mock('../api/evaluationRuns', () => ({
  fetchEvaluationRuns: api.list,
  fetchEvaluationRun: api.detail,
  fetchEvaluationCases: api.cases,
}))

const run = { run_key: 'candidate-run', mode: 'retrieval', status: 'completed', code_sha: 'a'.repeat(40), artifact_sha256: 'b'.repeat(64) }
const detail = {
  ...run,
  versions: { index_key: 'reviewed-index', dataset_manifest_sha256: 'c'.repeat(64), corpus_manifest_sha256: 'd'.repeat(64), policy_version: 'hybrid-rrf-v1' },
  environment: { os: 'test' },
  metrics: { case_count: 36, mrr: 0.8 },
  limitations: ['No semantic judge.'],
  review: { decision: 'approved' },
  comparison_run_key: 'baseline-run',
  metric_deltas: { case_count: 0, mrr: 0.05 },
}
const failedCase = { case_id: 'dev-01', split: 'development', question: 'What is the purpose?', answerable: true, status: 'failed', retrieved_evidence_ids: [], relevant_evidence_ids: ['evidence-1'], metric_values: { retrieval_hit: 0 } }

describe('evaluation results workbench', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders accessible identity, metric deltas, limitations, and failed-case evidence', async () => {
    api.list.mockResolvedValue({ items: [run, { ...run, run_key: 'baseline-run' }], next_cursor: null })
    api.detail.mockResolvedValue(detail)
    api.cases.mockResolvedValue({ items: [failedCase], next_cursor: null })
    render(<ResultsWorkbench />)

    expect(await screen.findByRole('heading', { name: 'Evaluation results' })).toBeInTheDocument()
    expect(screen.getByLabelText('Run')).toHaveValue('candidate-run')
    expect(await screen.findByText('80.0%')).toBeInTheDocument()
    expect(screen.getByText('+5.0 pp vs baseline-run')).toBeInTheDocument()
    expect(screen.getByText('No semantic judge.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /dev-01: What is the purpose/ })).toBeInTheDocument()
    expect(screen.getByText('evidence-1')).toBeInTheDocument()
    expect(screen.getByLabelText('Status')).toBeInTheDocument()
  })

  it('supports empty, error, retry, and status-filter states', async () => {
    api.list.mockRejectedValueOnce(new Error('private server detail')).mockResolvedValueOnce({ items: [], next_cursor: null })
    render(<ResultsWorkbench />)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('could not be loaded')
    expect(alert).toHaveFocus()
    expect(screen.queryByText('private server detail')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('No reviewed evaluation runs are available.')).toBeInTheDocument()
  })

  it('sends the selected case status to the bounded API', async () => {
    api.list.mockResolvedValue({ items: [run], next_cursor: null })
    api.detail.mockResolvedValue({ ...detail, comparison_run_key: null, metric_deltas: null })
    api.cases.mockResolvedValue({ items: [failedCase], next_cursor: null })
    render(<ResultsWorkbench />)
    await screen.findByText('No semantic judge.')
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'failed' } })
    await waitFor(() => expect(api.cases).toHaveBeenLastCalledWith('candidate-run', 'failed', expect.any(AbortSignal)))
  })
})
