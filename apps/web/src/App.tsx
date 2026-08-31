import { type FormEvent, useRef, useState } from 'react'
import { fetchAnswerStream, type AskRequest } from './api/answerStream'
import { fetchSearchEvidence } from './api/search'
import { initialInspectionState, inspectionReducer } from './inspection/state'

const labels = { idle: 'Ready', submitting: 'Submitting question', retrieving: 'Retrieving evidence', streaming: 'Streaming answer', completed: 'Complete', failed: 'Failed', cancelled: 'Cancelled' } as const

export function App() {
  const [state, setState] = useState(initialInspectionState)
  const [question, setQuestion] = useState('')
  const [indexVersion, setIndexVersion] = useState('fixture-v1')
  const controller = useRef<AbortController | null>(null)
  const evidenceRefs = useRef<Record<string, HTMLElement | null>>({})
  const dispatch = (action: Parameters<typeof inspectionReducer>[1]) => setState((current) => inspectionReducer(current, action))
  const busy = state.phase === 'submitting' || state.phase === 'retrieving' || state.phase === 'streaming'

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || !indexVersion.trim()) return
    controller.current?.abort()
    const request: AskRequest = { question: question.trim(), index_version: indexVersion.trim(), retrieval_limit: 10, mode: 'fixture' }
    const abortController = new AbortController()
    controller.current = abortController
    dispatch({ type: 'submit', request })
    try {
      for await (const streamEvent of fetchAnswerStream(request, abortController.signal)) {
        if (abortController.signal.aborted) return
        dispatch({ type: 'stream_event', event: streamEvent })
        if (streamEvent.type === 'retrieval.completed') {
          try {
            const evidence = await fetchSearchEvidence(request.question, request.index_version, abortController.signal)
            if (!abortController.signal.aborted) dispatch({ type: 'evidence_loaded', evidence })
          } catch { if (!abortController.signal.aborted) dispatch({ type: 'evidence_failed' }) }
        }
      }
    } catch {
      if (abortController.signal.aborted) dispatch({ type: 'cancel' })
      else dispatch({ type: 'transport_failed', code: 'stream.transport' })
    } finally { if (controller.current === abortController) controller.current = null }
  }

  function cancel() { if (controller.current !== null) { controller.current.abort(); dispatch({ type: 'cancel' }) } }

  return <main>
    <header className="hero"><p className="eyebrow">Evidence inspection workbench</p><h1 id="page-title">EvalGate</h1><p className="summary">Ask a grounded question, watch the verified stream, and inspect the exact evidence behind each citation.</p></header>
    <section className="workbench" aria-labelledby="ask-heading">
      <div className="panel"><p className="eyebrow">Local fixture mode</p><h2 id="ask-heading">Inspect an answer</h2>
        <form onSubmit={(event) => void submit(event)}><label htmlFor="question">Question</label><textarea id="question" value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} required rows={4} /><label htmlFor="index-version">Index version</label><input id="index-version" value={indexVersion} maxLength={128} onChange={(event) => setIndexVersion(event.target.value)} required /><div className="actions"><button type="submit" disabled={busy || !question.trim() || !indexVersion.trim()}>Ask</button><button type="button" className="secondary" onClick={cancel} disabled={!busy}>Cancel</button></div></form>
        <p className="status" role="status" aria-live="polite">{labels[state.phase]}</p>{state.errorMessage && <p className="error" role="alert">{state.errorMessage}</p>}
      </div>
      <div className="panel answer-panel"><p className="eyebrow">Answer</p><h2 id="answer-heading">{state.answerStatus === 'insufficient_support' ? 'Insufficient support' : 'Grounded response'}</h2><p className="answer" aria-live="polite">{state.answer || (state.phase === 'idle' ? 'Your streamed answer will appear here.' : 'Waiting for answer text…')}</p>
        {state.citationsReady && state.citations.length > 0 && <div className="citations" aria-labelledby="citations-heading"><h3 id="citations-heading">Citations</h3>{state.citations.map((citation, index) => <button key={`${citation.evidence_id}-${index}`} type="button" className="citation" aria-controls={`evidence-${citation.evidence_id}`} onClick={() => evidenceRefs.current[citation.evidence_id]?.scrollIntoView({ behavior: 'smooth', block: 'center' })}>{citation.title} · {citation.section_key}</button>)}</div>}
      </div>
    </section>
    <section className="panel evidence-panel" aria-labelledby="evidence-heading"><p className="eyebrow">Inspectable sources</p><h2 id="evidence-heading">Evidence</h2>{state.evidence.length === 0 ? <p className="muted">Evidence appears after retrieval completes.</p> : state.evidence.map((item) => <article id={`evidence-${item.evidence_id}`} className="evidence" key={item.evidence_id} ref={(element) => { evidenceRefs.current[item.evidence_id] = element }}><h3>{item.title}</h3><p className="muted">{item.source_key} · {item.section_key} · rank {item.rank}</p><p>{item.content}</p><small>Evidence ID: {item.evidence_id}</small></article>)}</section>
  </main>
}
