import { type FormEvent, type RefObject, useEffect, useMemo, useRef, useState } from 'react'
import { fetchAnswerStream, type AskRequest } from './api/answerStream'
import { fetchInspectionCatalog, type InspectionCatalogItem } from './api/catalog'
import { ProblemResponseError } from './api/problem'
import { fetchSearchEvidence } from './api/search'
import { ResultsWorkbench } from './evaluation/ResultsWorkbench'
import { initialInspectionState, inspectionReducer, type InspectionState } from './inspection/state'
import { contentText } from './presentation/safeContent'

function browserDeadlineMs(): number {
  const configured = Number(import.meta.env.VITE_ASK_DEADLINE_MS)
  return Number.isInteger(configured) && configured >= 100 && configured <= 30_000 ? configured : 30_000
}

const ASK_DEADLINE_MS = browserDeadlineMs()
const routes = [
  { path: '/', label: 'Overview', title: 'Overview' },
  { path: '/inspect', label: 'Inspect', title: 'Inspect evidence' },
  { path: '/evaluations', label: 'Evaluations', title: 'Evaluation results' },
  { path: '/system-evidence', label: 'System evidence', title: 'System evidence' },
] as const
type Route = (typeof routes)[number]['path']

function routeFor(path: string): Route { return routes.some((route) => route.path === path) ? path as Route : '/' }
function titleCase(value: string): string { return value.replaceAll(/[-_]/g, ' ').replaceAll(/\b\w/g, (letter) => letter.toUpperCase()) }
function pageTitle(route: Route): string { return `EvalGate · ${routes.find((item) => item.path === route)?.title ?? 'Overview'}` }

function GateMark({ compact = false }: Readonly<{ compact?: boolean }>) {
  return <svg className={compact ? 'gate-mark gate-mark--compact' : 'gate-mark'} viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path d="M8 9h17v30H8z" fill="none" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" /><path d="M16 24h24M32 16l8 8-8 8" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" /><circle cx="16" cy="24" r="3" fill="currentColor" /></svg>
}

function Hint({ children }: Readonly<{ children: string }>) { return <span className="hint" tabIndex={0} aria-label={children}>i</span> }

function problemCode(error: unknown, timedOut: boolean): string {
  if (timedOut) return 'client.timeout'
  if (error instanceof ProblemResponseError) return error.problem.code
  if (error instanceof DOMException && error.name === 'AbortError') return 'stream.cancelled'
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return 'client.offline'
  if (error instanceof Error && error.name === 'AnswerStreamProtocolError') return 'stream.protocol'
  return 'stream.transport'
}

export function App() {
  const [route, setRoute] = useState<Route>(() => routeFor(window.location.pathname))
  const [state, setState] = useState(initialInspectionState)
  const [question, setQuestion] = useState('')
  const [catalog, setCatalog] = useState<readonly InspectionCatalogItem[] | null>(null)
  const [catalogError, setCatalogError] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState('')
  const controller = useRef<AbortController | null>(null)
  const deadline = useRef<number | null>(null)
  const activeRequest = useRef(0)
  const evidenceRefs = useRef<Record<string, HTMLElement | null>>({})
  const errorRef = useRef<HTMLDivElement | null>(null)
  const dispatch = (action: Parameters<typeof inspectionReducer>[1]) => setState((current) => inspectionReducer(current, action))
  const busy = state.phase === 'submitting' || state.phase === 'retrieving' || state.phase === 'streaming'
  const selected = useMemo(() => catalog?.find((item) => item.index_version === selectedIndex) ?? null, [catalog, selectedIndex])

  useEffect(() => { document.title = pageTitle(route) }, [route])
  useEffect(() => { const listener = () => setRoute(routeFor(window.location.pathname)); window.addEventListener('popstate', listener); return () => window.removeEventListener('popstate', listener) }, [])
  useEffect(() => {
    const catalogController = new AbortController()
    void fetchInspectionCatalog(catalogController.signal).then((items) => { setCatalog(items); setSelectedIndex((current) => current || items[0]?.index_version || '') }).catch(() => { if (!catalogController.signal.aborted) { setCatalog([]); setCatalogError(true) } })
    return () => catalogController.abort()
  }, [])
  useEffect(() => { if (state.errorMessage !== null) errorRef.current?.focus() }, [state.errorMessage])

  function navigate(next: Route) { if (next !== route) { window.history.pushState({}, '', next); setRoute(next) } }
  function clearRequest() { if (deadline.current !== null) window.clearTimeout(deadline.current); deadline.current = null; controller.current = null }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || selected === null) return
    controller.current?.abort()
    if (deadline.current !== null) window.clearTimeout(deadline.current)
    const request: AskRequest = { question: question.trim(), index_version: selected.index_version, retrieval_limit: 10, mode: 'fixture' }
    const abortController = new AbortController()
    const requestNumber = activeRequest.current + 1
    activeRequest.current = requestNumber
    let timedOut = false
    controller.current = abortController
    deadline.current = window.setTimeout(() => { timedOut = true; abortController.abort() }, ASK_DEADLINE_MS)
    dispatch({ type: 'submit', request })
    try {
      for await (const streamEvent of fetchAnswerStream(request, abortController.signal)) {
        if (activeRequest.current !== requestNumber || abortController.signal.aborted) return
        dispatch({ type: 'stream_event', event: streamEvent })
        if (streamEvent.type === 'retrieval.completed') {
          try {
            const evidence = await fetchSearchEvidence(request.question, request.index_version, abortController.signal)
            if (activeRequest.current === requestNumber && !abortController.signal.aborted) dispatch({ type: 'evidence_loaded', evidence })
          } catch (error) {
            if (activeRequest.current === requestNumber && !abortController.signal.aborted) dispatch({ type: 'transport_failed', code: problemCode(error, false) })
          }
        }
      }
    } catch (error) {
      if (activeRequest.current !== requestNumber) return
      const code = problemCode(error, timedOut)
      if (code === 'stream.cancelled') dispatch({ type: 'cancel' })
      else dispatch({ type: 'transport_failed', code })
    } finally { if (activeRequest.current === requestNumber) clearRequest() }
  }

  function cancel() { if (controller.current !== null) { activeRequest.current += 1; controller.current.abort(); clearRequest(); dispatch({ type: 'cancel' }) } }
  function focusEvidence(evidenceId: string) { const target = evidenceRefs.current[evidenceId]; if (target === undefined || target === null) return; const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false; target.scrollIntoView?.({ behavior: reduced ? 'auto' : 'smooth', block: 'center' }); target.focus({ preventScroll: true }) }

  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><header className="topbar"><a className="brand" href="/" onClick={(event) => { event.preventDefault(); navigate('/') }} aria-label="EvalGate overview"><GateMark compact /><span>EvalGate</span></a><nav aria-label="Primary navigation"><ul>{routes.map((item) => <li key={item.path}><a href={item.path} aria-current={route === item.path ? 'page' : undefined} onClick={(event) => { event.preventDefault(); navigate(item.path) }}>{item.label}</a></li>)}</ul></nav><span className="mode-chip" title="The browser only runs deterministic fixture answers. Governed live evidence is reviewed separately.">Local fixture mode</span></header><main id="main-content" className="page-content">{route === '/' ? <Overview onInspect={() => navigate('/inspect')} onEvaluations={() => navigate('/evaluations')} /> : null}{route === '/inspect' ? <Inspect question={question} setQuestion={setQuestion} catalog={catalog} catalogError={catalogError} selectedIndex={selectedIndex} setSelectedIndex={setSelectedIndex} selected={selected} state={state} busy={busy} errorRef={errorRef} evidenceRefs={evidenceRefs} submit={submit} cancel={cancel} focusEvidence={focusEvidence} /> : null}{route === '/evaluations' ? <Evaluations /> : null}{route === '/system-evidence' ? <SystemEvidence catalog={catalog} selected={selected} catalogError={catalogError} /> : null}</main><footer className="footer">EvalGate is a local evidence workbench. It is not deployed, and fixture mechanics are not model-quality evidence.</footer></div>
}

function Overview({ onInspect, onEvaluations }: Readonly<{ onInspect: () => void; onEvaluations: () => void }>) {
  return <><section className="hero"><div><p className="eyebrow">Evidence control room</p><h1>Know what changed before you ship.</h1><p className="lead">EvalGate helps teams inspect retrieval, grounded answers, citations, and reviewed evaluation evidence without hiding the underlying proof.</p><div className="actions actions--inline"><button type="button" onClick={onInspect}>Inspect an answer</button><button type="button" className="secondary" onClick={onEvaluations}>View evaluations</button></div></div><GateMark /></section><section className="flow" aria-labelledby="flow-heading"><p className="eyebrow">How it works</p><h2 id="flow-heading">From source material to a release decision</h2><ol><li><strong>1. Governed corpus</strong><span>Approved source material is versioned before retrieval.</span></li><li><strong>2. Retrieval</strong><span>Lexical and vector search produce inspectable evidence.</span></li><li><strong>3. Grounded answer</strong><span>Fixture-mode answers cite evidence that you can open.</span></li><li><strong>4. Evaluation gate</strong><span>Reviewed cases reveal regressions before a release claim.</span></li></ol></section><section className="notice" aria-labelledby="limits-heading"><h2 id="limits-heading">What this local view proves</h2><p>It proves supported retrieval and inspection mechanics. It does not claim a deployed service or a live-model quality result.</p></section></>
}

type InspectProps = Readonly<{ question: string; setQuestion: (value: string) => void; catalog: readonly InspectionCatalogItem[] | null; catalogError: boolean; selectedIndex: string; setSelectedIndex: (value: string) => void; selected: InspectionCatalogItem | null; state: InspectionState; busy: boolean; errorRef: RefObject<HTMLDivElement | null>; evidenceRefs: RefObject<Record<string, HTMLElement | null>>; submit: (event: FormEvent) => Promise<void>; cancel: () => void; focusEvidence: (id: string) => void }>

function Inspect({ question, setQuestion, catalog, catalogError, selectedIndex, setSelectedIndex, selected, state, busy, errorRef, evidenceRefs, submit, cancel, focusEvidence }: InspectProps) {
  const samples = ['What should an operator record after an incident?', 'Which evidence supports the rollback procedure?']
  return <><header className="page-header"><p className="eyebrow">Inspection</p><h1>Trace an answer to its evidence.</h1><p>Choose a governed source, ask one focused question, then inspect retrieval and citations. Technical identifiers stay available below when you need them.</p></header><section className="stage-strip" aria-label="Answer processing stages"><span className={busy || state.phase === 'completed' ? 'stage stage--active' : 'stage'}>Retrieve</span><span className={state.phase === 'streaming' || state.phase === 'completed' ? 'stage stage--active' : 'stage'}>Answer</span><span className={state.citationsReady ? 'stage stage--active' : 'stage'}>Validate citations</span></section><section className="inspection-grid" aria-labelledby="ask-heading"><div className="panel"><p className="eyebrow">Guided request</p><h2 id="ask-heading">Ask a grounded question <Hint>Answers use deterministic fixture mode in this local browser. The evidence path remains inspectable.</Hint></h2><form onSubmit={(event) => void submit(event)}><label htmlFor="catalog">Evidence source</label>{catalog === null ? <p role="status">Loading available evidence sources…</p> : null}{catalogError ? <div className="result-error" role="alert">Available sources could not be loaded. Refresh the page to try again.</div> : null}{catalog !== null && !catalogError ? <select id="catalog" value={selectedIndex} onChange={(event) => setSelectedIndex(event.target.value)} disabled={catalog.length === 0}>{catalog.length === 0 ? <option value="">No governed source is available</option> : catalog.map((item) => <option key={item.index_version} value={item.index_version}>{item.label}</option>)}</select> : null}<label htmlFor="question">Your question</label><textarea id="question" value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} required rows={4} placeholder="Ask about a process, policy, or decision…" /><div className="sample-questions"><span>Try an example:</span>{samples.map((sample) => <button type="button" className="text-button" key={sample} onClick={() => setQuestion(sample)}>{sample}</button>)}</div><div className="actions"><button type="submit" disabled={busy || !question.trim() || selected === null}>Inspect answer</button><button type="button" className="secondary" onClick={cancel} disabled={!busy}>Cancel request</button></div></form><p className="status" role="status" aria-live="polite" aria-atomic="true">{titleCase(state.phase)}</p>{state.errorMessage ? <div ref={errorRef} className="result-error" role="alert" tabIndex={-1}><strong>{state.errorMessage}</strong><p><code>{state.errorCode}</code></p><button type="button" className="secondary compact" onClick={(event) => event.currentTarget.closest('form')?.requestSubmit()}>Try again</button></div> : null}</div><AnswerPanel state={state} focusEvidence={focusEvidence} /></section><section className="panel evidence-panel" aria-labelledby="evidence-heading"><p className="eyebrow">Inspectable sources</p><h2 id="evidence-heading">Retrieved evidence</h2>{state.evidence.length === 0 ? <div className="empty-state"><img src="/evalgate-mark.svg" alt="" /><p className="muted">Retrieved source passages appear here after the answer request reaches the retrieval stage.</p></div> : state.evidence.map((item) => <article id={`evidence-${item.evidence_id}`} className="evidence" key={item.evidence_id} ref={(element) => { evidenceRefs.current[item.evidence_id] = element }} tabIndex={-1}><div><span className="rank">Evidence {item.rank}</span><h3>{contentText(item.title)}</h3></div><p className="muted">{contentText(item.source_key)} · {contentText(item.section_key)}</p><p>{contentText(item.content)}</p><details><summary>Technical details</summary><dl className="technical-list"><div><dt>Evidence ID</dt><dd><code>{contentText(item.evidence_id)}</code></dd></div><div><dt>Content checksum</dt><dd><code>{contentText(item.content_sha256)}</code></dd></div></dl></details></article>)}</section></>
}

function AnswerPanel({ state, focusEvidence }: Readonly<{ state: InspectionState; focusEvidence: (id: string) => void }>) {
  return <div className="panel answer-panel"><p className="eyebrow">Grounded answer</p><h2>{state.answerStatus === 'insufficient_support' ? 'Insufficient support' : 'Answer and citations'}</h2><p className="answer">{contentText(state.answer || (state.phase === 'idle' ? 'Your evidence-grounded answer will appear here.' : 'Working through the supported evidence…'))}</p>{state.citationsReady && state.citations.length > 0 ? <div className="citations"><h3>Citations</h3>{state.citations.map((citation, index) => <button key={`${citation.evidence_id}-${index}`} type="button" className="citation" aria-controls={`evidence-${citation.evidence_id}`} onClick={() => focusEvidence(citation.evidence_id)}>{contentText(citation.title)} · {contentText(citation.section_key)}</button>)}</div> : null}{state.provider ? <details><summary>Technical details</summary><p><code>{contentText(state.provider.name)} · {contentText(state.provider.revision)}</code></p></details> : null}</div>
}

function Evaluations() { return <><header className="page-header"><p className="eyebrow">Read-only evaluation evidence</p><h1>Review regressions before release.</h1><p>Start with the reviewed run summary, then filter to failed cases and inspect their evidence.</p></header><ResultsWorkbench /></> }

function SystemEvidence({ catalog, selected, catalogError }: Readonly<{ catalog: readonly InspectionCatalogItem[] | null; selected: InspectionCatalogItem | null; catalogError: boolean }>) {
  return <><header className="page-header"><p className="eyebrow">System evidence</p><h1>See what this local workbench is using.</h1><p>Names come first. Immutable identifiers remain available for reproduction and audit.</p></header><section className="panel"><h2>Current inspection source</h2>{catalog === null ? <p role="status">Loading source identity…</p> : null}{catalogError ? <p className="result-error">Source identity is unavailable while the catalog cannot be reached.</p> : null}{selected ? <><dl className="identity-grid"><div><dt>Corpus</dt><dd>{contentText(titleCase(selected.corpus_key))}</dd></div><div><dt>Corpus version</dt><dd>{contentText(selected.corpus_version)}</dd></div><div><dt>Index policy</dt><dd>{contentText(titleCase(selected.index_key))}</dd></div><div><dt>Browser mode</dt><dd>Deterministic fixture</dd></div></dl><details><summary>Technical details</summary><dl className="technical-list"><div><dt>Index version ID</dt><dd><code>{contentText(selected.index_version)}</code></dd></div><div><dt>Corpus key</dt><dd><code>{contentText(selected.corpus_key)}</code></dd></div></dl></details></> : null}</section><section className="notice"><h2>Evidence status</h2><p>Local fixture answers demonstrate contract behavior. Reviewed retrieval and governed live artifacts have separate limitations; neither is a deployment claim.</p></section></>
}
