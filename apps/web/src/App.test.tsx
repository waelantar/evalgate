import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

const stream = vi.hoisted(() => ({ events: [] as Array<Record<string, unknown>>, fail: false }))
const search = vi.hoisted(() => ({ evidence: [{ rank: 1, evidence_id: 'ev-1', document_id: 'doc-1', source_key: 'fixture', title: 'Runbook', license_id: 'internal', provenance: 'fixture', section_key: 'intro', source_start: 0, source_end: 10, content: 'Verified evidence', content_sha256: 'hash', lexical_rank: 1, vector_rank: null, rrf_score: 1 }] }))
vi.mock('./api/answerStream', () => ({
  fetchAnswerStream: async function* () { await Promise.resolve(); if (stream.fail) throw new Error('secret'); for (const event of stream.events) yield event },
}))
vi.mock('./api/search', () => ({ fetchSearchEvidence: vi.fn(() => Promise.resolve(search.evidence)) }))
vi.mock('./api/evaluationRuns', () => ({
  fetchEvaluationRuns: vi.fn().mockResolvedValue({ items: [], next_cursor: null }),
  fetchEvaluationRun: vi.fn(),
  fetchEvaluationCases: vi.fn(),
}))

const envelope = (type: string, sequence: number, extra: Record<string, unknown> = {}) => ({ schema_version: '1.0', request_id: 'req-1', sequence, type, ...extra })

describe('inspection workbench', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    stream.events = []
    stream.fail = false
    search.evidence = [{ rank: 1, evidence_id: 'ev-1', document_id: 'doc-1', source_key: 'fixture', title: 'Runbook', license_id: 'internal', provenance: 'fixture', section_key: 'intro', source_start: 0, source_end: 10, content: 'Verified evidence', content_sha256: 'hash', lexical_rank: 1, vector_rank: null, rrf_score: 1 }]
  })

  it('renders streamed answer, evidence, and citation navigation', async () => {
    stream.events = [
      envelope('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } }),
      envelope('retrieval.completed', 2, { index_version: 'fixture-v1', corpus_version: 'fixture-c1', evidence_ids: ['ev-1'] }),
      envelope('answer.delta', 3, { text: 'Grounded answer' }),
      envelope('citations.completed', 4, { citations: [{ evidence_id: 'ev-1', title: 'Runbook', section_key: 'intro' }] }),
      envelope('answer.completed', 5, { status: 'answered', provider: { mode: 'fixture', name: 'fixture', revision: '1' } }),
    ]
    render(<App />)
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText('Grounded answer')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Runbook/ })).toHaveAttribute('aria-controls', 'evidence-ev-1')
    expect(await screen.findByText('Verified evidence')).toBeInTheDocument()
  })

  it('shows a safe failure message for transport errors', async () => {
    stream.events = []
    stream.fail = true
    render(<App />)
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The answer could not be loaded')
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('renders XSS text and invalid schemes without creating active elements', async () => {
    const payload = '<img src=x onerror=alert(1)>'
    const unsafeScheme = 'javascript:alert(1)'
    search.evidence = [{ ...search.evidence[0]!, title: unsafeScheme, content: payload }]
    stream.events = [
      envelope('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } }),
      envelope('retrieval.completed', 2, { index_version: 'fixture-v1', corpus_version: 'fixture-c1', evidence_ids: ['ev-1'] }),
      envelope('answer.delta', 3, { text: payload }),
      envelope('citations.completed', 4, { citations: [{ evidence_id: 'ev-1', title: unsafeScheme, section_key: 'intro' }] }),
      envelope('answer.completed', 5, { status: 'answered', provider: { mode: 'fixture', name: 'fixture', revision: '1' } }),
    ]

    render(<App />)
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findAllByText(payload)).toHaveLength(2)
    expect(screen.getByRole('button', { name: /javascript:alert/ })).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull()
  })
})
