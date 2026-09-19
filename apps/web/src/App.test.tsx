import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

const stream = vi.hoisted(() => ({ events: [] as Array<Record<string, unknown>>, fail: false, hold: false, release: null as (() => void) | null }))
const search = vi.hoisted(() => ({ evidence: [{ rank: 1, evidence_id: 'ev-1', document_id: 'doc-1', source_key: 'fixture', title: 'Runbook', license_id: 'internal', provenance: 'fixture', section_key: 'intro', source_start: 0, source_end: 10, content: 'Verified evidence', content_sha256: 'hash', lexical_rank: 1, vector_rank: null, rrf_score: 1 }] }))
vi.mock('./api/answerStream', () => ({
  fetchAnswerStream: async function* () { await Promise.resolve(); if (stream.fail) throw new Error('secret'); for (const event of stream.events) yield event; if (stream.hold) await new Promise<void>((resolve) => { stream.release = resolve }) },
}))
vi.mock('./api/search', () => ({ fetchSearchEvidence: vi.fn(() => Promise.resolve(search.evidence)) }))
vi.mock('./api/catalog', () => ({
  fetchInspectionCatalog: vi.fn().mockResolvedValue([{
    index_version: 'fixture-v1',
    index_key: 'fixture-index',
    corpus_key: 'fixture-corpus',
    corpus_version: '1.0.0',
    label: 'Fixture corpus · 1.0.0',
  }]),
}))
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
    stream.hold = false
    stream.release?.()
    stream.release = null
    search.evidence = [{ rank: 1, evidence_id: 'ev-1', document_id: 'doc-1', source_key: 'fixture', title: 'Runbook', license_id: 'internal', provenance: 'fixture', section_key: 'intro', source_start: 0, source_end: 10, content: 'Verified evidence', content_sha256: 'hash', lexical_rank: 1, vector_rank: null, rrf_score: 1 }]
  })

  async function openInspect(): Promise<void> {
    fireEvent.click(screen.getByRole('link', { name: 'Inspect' }))
    await screen.findByLabelText('Evidence source')
  }

  it('renders streamed answer, evidence, and citation navigation', async () => {
    stream.events = [
      envelope('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } }),
      envelope('retrieval.completed', 2, { index_version: 'fixture-v1', corpus_version: 'fixture-c1', evidence_ids: ['ev-1'] }),
      envelope('answer.delta', 3, { text: 'Grounded answer' }),
      envelope('citations.completed', 4, { citations: [{ evidence_id: 'ev-1', title: 'Runbook', section_key: 'intro' }] }),
      envelope('answer.completed', 5, { status: 'answered', provider: { mode: 'fixture', name: 'fixture', revision: '1' } }),
    ]
    render(<App />)
    await openInspect()
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect answer' }))
    expect(await screen.findByText('Grounded answer')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Runbook/ })).toHaveAttribute('aria-controls', 'evidence-ev-1')
    expect(await screen.findByText('Verified evidence')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Runbook/ }))
    expect(document.getElementById('evidence-ev-1')).toHaveFocus()
  })

  it('uses instant citation movement when reduced motion is requested', async () => {
    const originalMatchMedia = Object.getOwnPropertyDescriptor(window, 'matchMedia')
    const originalScrollIntoView = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView')
    const scrollIntoView = vi.fn()
    Object.defineProperty(window, 'matchMedia', { configurable: true, value: (query: string) => ({ matches: true, media: query }) as MediaQueryList })
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scrollIntoView })
    stream.events = [
      envelope('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } }),
      envelope('retrieval.completed', 2, { index_version: 'fixture-v1', corpus_version: 'fixture-c1', evidence_ids: ['ev-1'] }),
      envelope('answer.delta', 3, { text: 'Grounded answer' }),
      envelope('citations.completed', 4, { citations: [{ evidence_id: 'ev-1', title: 'Runbook', section_key: 'intro' }] }),
      envelope('answer.completed', 5, { status: 'answered', provider: { mode: 'fixture', name: 'fixture', revision: '1' } }),
    ]
    try {
      render(<App />)
      await openInspect()
      fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'How?' } })
      fireEvent.click(screen.getByRole('button', { name: 'Inspect answer' }))
      fireEvent.click(await screen.findByRole('button', { name: /Runbook/ }))
      expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'center' })
    } finally {
      if (originalMatchMedia === undefined) Reflect.deleteProperty(window, 'matchMedia')
      else Object.defineProperty(window, 'matchMedia', originalMatchMedia)
      if (originalScrollIntoView === undefined) Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
      else Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScrollIntoView)
    }
  })

  it('shows a safe failure message for transport errors', async () => {
    stream.events = []
    stream.fail = true
    render(<App />)
    await openInspect()
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect answer' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('The answer could not be loaded')
    expect(alert).toHaveFocus()
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('keeps cancellation keyboard-reachable and announces the cancelled state', async () => {
    stream.events = [envelope('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } })]
    stream.hold = true
    render(<App />)
    await openInspect()
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect answer' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Retrieving')
    const cancel = screen.getByRole('button', { name: 'Cancel request' })
    cancel.focus()
    fireEvent.keyDown(cancel, { key: 'Enter' })
    fireEvent.click(cancel)
    expect(screen.getByRole('status')).toHaveTextContent('Cancelled')
    stream.release?.()
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
    await openInspect()
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'How?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect answer' }))

    expect(await screen.findAllByText(payload)).toHaveLength(2)
    expect(screen.getByRole('button', { name: /javascript:alert/ })).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull()
  })

  it('renders the read-only Kubernetes showcase with source limitations', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('link', { name: 'Showcase' }))

    expect(await screen.findByRole('heading', { name: /Kubernetes debug documentation/ })).toBeInTheDocument()
    expect(screen.getByText('11 Markdown files')).toBeInTheDocument()
    expect(screen.getByText('18 reviewed cases')).toBeInTheDocument()
    expect(screen.getByText(/not a public benchmark/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /run/i })).not.toBeInTheDocument()
  })
})
