import { type FormEvent, type RefObject, useEffect, useMemo, useRef, useState } from 'react'
import { fetchAnswerStream, type AskRequest } from './api/answerStream'
import { fetchInspectionCatalog, type InspectionCatalogItem } from './api/catalog'
import { Picker } from './components/Picker'
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
  { path: '/data', label: 'Bring data', title: 'Bring your data' },
  { path: '/evaluations', label: 'Evaluations', title: 'Evaluation results' },
  { path: '/showcase', label: 'Showcase', title: 'Real-world showcase' },
  { path: '/system-evidence', label: 'System evidence', title: 'System evidence' },
] as const
type Route = (typeof routes)[number]['path']

function routeFor(path: string): Route { return routes.some((route) => route.path === path) ? path as Route : '/' }
function titleCase(value: string): string { return value.replaceAll(/[-_]/g, ' ').replaceAll(/\b\w/g, (letter) => letter.toUpperCase()) }
function pageTitle(route: Route): string { return `EvalGate - ${routes.find((item) => item.path === route)?.title ?? 'Overview'}` }

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
  const [menuOpen, setMenuOpen] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('evalgate-theme') === 'dark' ? 'dark' : 'light')
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
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('evalgate-theme', theme) }, [theme])
  useEffect(() => { const listener = () => setRoute(routeFor(window.location.pathname)); window.addEventListener('popstate', listener); return () => window.removeEventListener('popstate', listener) }, [])
  useEffect(() => {
    const catalogController = new AbortController()
    void fetchInspectionCatalog(catalogController.signal).then((items) => { setCatalog(items); setSelectedIndex((current) => current || items[0]?.index_version || '') }).catch(() => { if (!catalogController.signal.aborted) { setCatalog([]); setCatalogError(true) } })
    return () => catalogController.abort()
  }, [])
  useEffect(() => { if (state.errorMessage !== null) errorRef.current?.focus() }, [state.errorMessage])

  function navigate(next: Route) { setMenuOpen(false); if (next !== route) { window.history.pushState({}, '', next); setRoute(next) } }
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

  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><header className="topbar"><a className="brand" href="/" onClick={(event) => { event.preventDefault(); navigate('/') }} aria-label="EvalGate overview"><GateMark compact /><span>EvalGate</span></a><button type="button" className="menu-toggle" aria-expanded={menuOpen} aria-controls="primary-navigation" onClick={() => setMenuOpen((current) => !current)}><span aria-hidden="true" className="menu-icon">=</span>Menu</button><nav id="primary-navigation" className={menuOpen ? 'primary-nav primary-nav--open' : 'primary-nav'} aria-label="Primary navigation"><ul>{routes.map((item) => <li key={item.path}><a href={item.path} aria-current={route === item.path ? 'page' : undefined} onClick={(event) => { event.preventDefault(); navigate(item.path) }}>{item.label}</a></li>)}</ul></nav><button type="button" className="theme-toggle" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'night'} mode`} onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? 'Light' : 'Night'}</button><span className="mode-chip mode-chip--fixture" title="This browser demo answers with deterministic fixtures. Your own corpora are ingested locally before inspection."><span className="mode-dot" aria-hidden="true" />Local fixture mode</span></header><main id="main-content" className="page-content">{route === '/' ? <Overview onInspect={() => navigate('/inspect')} onData={() => navigate('/data')} onEvaluations={() => navigate('/evaluations')} /> : null}{route === '/inspect' ? <Inspect question={question} setQuestion={setQuestion} catalog={catalog} catalogError={catalogError} selectedIndex={selectedIndex} setSelectedIndex={setSelectedIndex} selected={selected} state={state} busy={busy} errorRef={errorRef} evidenceRefs={evidenceRefs} submit={submit} cancel={cancel} focusEvidence={focusEvidence} /> : null}{route === '/data' ? <BringData /> : null}{route === '/evaluations' ? <Evaluations /> : null}{route === '/showcase' ? <Showcase /> : null}{route === '/system-evidence' ? <SystemEvidence catalog={catalog} selected={selected} catalogError={catalogError} /> : null}</main><footer className="footer">EvalGate is a local evidence workbench. It is not deployed, and fixture mechanics are not model-quality evidence.</footer></div>
}

function Overview({ onInspect, onData, onEvaluations }: Readonly<{ onInspect: () => void; onData: () => void; onEvaluations: () => void }>) {
  return <><section className="hero"><div><p className="eyebrow">Evidence control room</p><h1>Know what changed before you ship.</h1><p className="lead">EvalGate helps teams inspect retrieval, grounded answers, citations, and reviewed evaluation evidence without hiding the underlying proof.</p><div className="actions actions--inline"><button type="button" onClick={onInspect}>Inspect an answer</button><button type="button" className="secondary" onClick={onData}>Bring your data</button><button type="button" className="secondary" onClick={onEvaluations}>View evaluations</button></div></div><GateMark /></section><section className="flow" aria-labelledby="flow-heading"><p className="eyebrow">How it works</p><h2 id="flow-heading">From source material to a release decision</h2><ol><li><strong>1. Governed corpus</strong><span>Approved source material is versioned before retrieval.</span></li><li><strong>2. Retrieval</strong><span>Lexical and vector search produce inspectable evidence.</span></li><li><strong>3. Grounded answer</strong><span>Fixture-mode answers cite evidence that you can open.</span></li><li><strong>4. Evaluation gate</strong><span>Reviewed cases reveal regressions before a release claim.</span></li></ol></section><section className="panel data-onramp"><div><p className="eyebrow">For a new team</p><h2>Start with your own documents, not the demo data.</h2><p>Northstar and Kubernetes are included examples. A real EvalGate workspace starts when you register a governed corpus, ingest it locally, then write reviewed questions against that source.</p></div><button type="button" className="secondary" onClick={onData}>See the data workflow</button></section></>
}

function BringData() {
  const workflow = [
    ['Prepare source files', 'Choose the docs, policies, runbooks, or tickets you are allowed to evaluate. Keep secrets and personal data out of the corpus unless a later private deployment explicitly supports them.'],
    ['Create a manifest', 'Declare corpus key, version, license/provenance, source paths, hashes, and the chunking/index policy before ingestion.'],
    ['Ingest locally', 'Run the local admin ingestion command so EvalGate creates immutable corpus, document, chunk, embedding, and index rows.'],
    ['Review questions', 'Author answerable and unanswerable cases with expected evidence IDs before any model comparison.'],
    ['Run and compare', 'Use the same corpus, index, prompt policy, schema, and budget for every model so failures stay comparable.'],
  ]
  return <><header className="page-header"><p className="eyebrow">Bring your data</p><h1>How a real user changes the source material.</h1><p>The browser does not accept arbitrary uploads yet. That is intentional: EvalGate treats company data as governed evidence, so a corpus is registered, checked, ingested, and reviewed before it appears in Inspect or Evaluations.</p></header><section className="panel"><div className="section-heading"><div><p className="eyebrow">Current product boundary</p><h2>Examples are preloaded; your corpus enters through local governance.</h2></div><span className="tag tag--blue">No browser secret or upload</span></div><p>Today you change values by adding a corpus manifest and running the local ingestion workflow. After ingestion, the new corpus appears in the Evidence source selector with a human-readable name; UUIDs and hashes remain inside technical details.</p><dl className="technical-list"><div><dt>Demo corpora</dt><dd>Northstar Operations and Kubernetes Debug Cluster</dd></div><div><dt>User data path</dt><dd>Manifest + local ingestion + reviewed cases</dd></div><div><dt>Current limitation</dt><dd>No arbitrary public upload or hosted private workspace in this local build.</dd></div></dl></section><section className="panel capability-panel" aria-labelledby="capability-heading"><p className="eyebrow">Product lanes to add</p><h2 id="capability-heading">The missing self-serve experience</h2><div className="capability-grid"><article><strong>Self-serve browser upload</strong><span>Upload approved documents, see license/privacy checks, preview chunks, then submit them for governed ingestion instead of editing manifests by hand.</span></article><article><strong>Account workspace</strong><span>Separate teams, corpora, evaluations, members, roles, audit logs, and model budgets so a non-technical user can work safely.</span></article><article><strong>Hosted private storage</strong><span>Keep source files, derived chunks, embeddings, artifacts, and review records in tenant-isolated encrypted storage with retention controls.</span></article></div></section><section className="flow data-flow" aria-labelledby="data-flow-heading"><p className="eyebrow">Workflow</p><h2 id="data-flow-heading">The company-style setup before production use</h2><ol>{workflow.map(([title, detail], index) => <li key={title}><strong>{index + 1}. {title}</strong><span>{detail}</span></li>)}</ol></section><section className="panel"><p className="eyebrow">Developer handoff</p><h2>What needs to be created for a new corpus</h2><ul className="evidence-list"><li>Source files under an approved data location.</li><li>A corpus manifest with license, provenance, hash, and path allowlist.</li><li>An index policy describing chunking and retrieval behavior.</li><li>A reviewed evaluation dataset with evidence IDs after ingestion.</li><li>Optional live-provider approval with model slugs, privacy posture, budget cap, and stop limit.</li></ul><details><summary>Local commands are intentionally admin-only</summary><dl className="technical-list"><div><dt>Ingestion entry point</dt><dd><code>evalgate-ingest</code></dd></div><div><dt>Evaluation import</dt><dd><code>evalgate-import-results</code></dd></div><div><dt>Reason</dt><dd>Prevents accidental public mutation, secret leakage, or unreviewed benchmark claims.</dd></div></dl></details></section></>
}

type InspectProps = Readonly<{ question: string; setQuestion: (value: string) => void; catalog: readonly InspectionCatalogItem[] | null; catalogError: boolean; selectedIndex: string; setSelectedIndex: (value: string) => void; selected: InspectionCatalogItem | null; state: InspectionState; busy: boolean; errorRef: RefObject<HTMLDivElement | null>; evidenceRefs: RefObject<Record<string, HTMLElement | null>>; submit: (event: FormEvent) => Promise<void>; cancel: () => void; focusEvidence: (id: string) => void }>

function Inspect({ question, setQuestion, catalog, catalogError, selectedIndex, setSelectedIndex, selected, state, busy, errorRef, evidenceRefs, submit, cancel, focusEvidence }: InspectProps) {
  const samples = ['What should an operator record after an incident?', 'Which evidence supports the rollback procedure?']
  return <><header className="page-header"><p className="eyebrow">Inspection</p><h1>Trace an answer to its evidence.</h1><p>Choose a governed source, ask one focused question, then inspect retrieval and citations. Technical identifiers stay available below when you need them.</p></header><section className="stage-strip" aria-label="Answer processing stages"><span className={busy || state.phase === 'completed' ? 'stage stage--active' : 'stage'}>Retrieve</span><span className={state.phase === 'streaming' || state.phase === 'completed' ? 'stage stage--active' : 'stage'}>Answer</span><span className={state.citationsReady ? 'stage stage--active' : 'stage'}>Validate citations</span></section><section className="inspection-grid" aria-labelledby="ask-heading"><div className="panel"><p className="eyebrow">Guided request</p><h2 id="ask-heading">Ask a grounded question <Hint>Answers use deterministic fixture mode in this local browser. The evidence path remains inspectable.</Hint></h2><form onSubmit={(event) => void submit(event)}>{catalog === null ? <p role="status">Loading available evidence sources</p> : null}{catalogError ? <div className="result-error" role="alert">Available sources could not be loaded. Refresh the page to try again.</div> : null}{catalog !== null && !catalogError ? <Picker id="catalog" label="Evidence source" value={selectedIndex} onChange={setSelectedIndex} disabled={catalog.length === 0} emptyLabel="No governed source is available" options={catalog.map((item) => ({ value: item.index_version, label: item.label, detail: `${titleCase(item.corpus_key)} / ${item.corpus_version}` }))} /> : null}<label htmlFor="question">Your question</label><textarea id="question" value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} required rows={4} placeholder="Ask about a process, policy, or decision" /><div className="sample-questions"><span>Try an example:</span>{samples.map((sample) => <button type="button" className="text-button" key={sample} onClick={() => setQuestion(sample)}>{sample}</button>)}</div><div className="actions"><button type="submit" disabled={busy || !question.trim() || selected === null}>Inspect answer</button><button type="button" className="secondary" onClick={cancel} disabled={!busy}>Cancel request</button></div></form>{state.phase !== 'idle' ? <p className="status" role="status" aria-live="polite" aria-atomic="true">{titleCase(state.phase)}</p> : null}{state.errorMessage ? <div ref={errorRef} className="result-error" role="alert" tabIndex={-1}><strong>{state.errorMessage}</strong><p><code>{state.errorCode}</code></p><button type="button" className="secondary compact" onClick={(event) => event.currentTarget.closest('form')?.requestSubmit()}>Try again</button></div> : null}</div><AnswerPanel state={state} focusEvidence={focusEvidence} /></section><section className="panel evidence-panel" aria-labelledby="evidence-heading"><p className="eyebrow">Inspectable sources</p><h2 id="evidence-heading">Retrieved evidence</h2>{state.evidence.length === 0 ? <div className="empty-state"><img src="/evalgate-mark.svg" alt="" /><p className="muted">Retrieved source passages appear here after the answer request reaches the retrieval stage.</p></div> : state.evidence.map((item) => <article id={`evidence-${item.evidence_id}`} className="evidence" key={item.evidence_id} ref={(element) => { evidenceRefs.current[item.evidence_id] = element }} tabIndex={-1}><div><span className="rank">Evidence {item.rank}</span><h3>{contentText(item.title)}</h3></div><p className="muted">{contentText(item.source_key)} / {contentText(item.section_key)}</p><p>{contentText(item.content)}</p><details><summary>Technical details</summary><dl className="technical-list"><div><dt>Evidence ID</dt><dd><code>{contentText(item.evidence_id)}</code></dd></div><div><dt>Content checksum</dt><dd><code>{contentText(item.content_sha256)}</code></dd></div></dl></details></article>)}</section></>
}

function AnswerPanel({ state, focusEvidence }: Readonly<{ state: InspectionState; focusEvidence: (id: string) => void }>) {
  return <div className="panel answer-panel"><p className="eyebrow">Grounded answer</p><h2>{state.answerStatus === 'insufficient_support' ? 'Insufficient support' : 'Answer and citations'}</h2><p className="answer">{contentText(state.answer || (state.phase === 'idle' ? 'Your evidence-grounded answer will appear here.' : 'Working through the supported evidence'))}</p>{state.citationsReady && state.citations.length > 0 ? <div className="citations"><h3>Citations</h3>{state.citations.map((citation, index) => <button key={`${citation.evidence_id}-${index}`} type="button" className="citation" aria-controls={`evidence-${citation.evidence_id}`} onClick={() => focusEvidence(citation.evidence_id)}>{contentText(citation.title)} / {contentText(citation.section_key)}</button>)}</div> : null}{state.provider ? <details><summary>Technical details</summary><p><code>{contentText(state.provider.name)} / {contentText(state.provider.revision)}</code></p></details> : null}</div>
}

function Evaluations() { return <><header className="page-header"><p className="eyebrow">Read-only evaluation evidence</p><h1>Review regressions before release.</h1><p>Start with the reviewed run summary, then filter to failed cases and inspect their evidence.</p></header><ResultsWorkbench /></> }


function Showcase() {
  const sourceFiles = [
    ['_index.md', 'Debug cluster landing page'],
    ['audit.md', 'Audit policy and log troubleshooting'],
    ['crictl.md', 'CRI runtime debugging with crictl'],
    ['kubectl-node-debug.md', 'Node debugging with kubectl'],
    ['local-debugging.md', 'Local cluster debugging workflow'],
    ['monitor-node-health.md', 'Node health monitoring'],
    ['resource-metrics-pipeline.md', 'Metrics pipeline setup'],
    ['resource-usage-monitoring.md', 'Resource usage monitoring'],
    ['topology.md', 'Topology and placement inspection'],
    ['troubleshoot-kubectl.md', 'kubectl troubleshooting'],
    ['windows.md', 'Windows node debugging notes'],
  ]
  const modelResults = [
    {
      model: 'deepseek/deepseek-v4-flash',
      result: '3 / 18 passed',
      passRate: '16.67%',
      citationRecall: '16.67%',
      judge: '28.57% over 14 judge labels',
      cost: '$0.001457442',
      status: 'limited-pass',
      note: 'Completed the comparable run; results remain too weak for a quality claim.',
    },
    {
      model: 'deepseek/deepseek-v4-flash-0731',
      result: '4 / 18 passed',
      passRate: '22.22%',
      citationRecall: '22.22%',
      judge: '36.36% over 11 judge labels',
      cost: '$0.003003420',
      status: 'limited-pass',
      note: 'Highest observed pass rate, but five unavailable cases and one timeout make it unreliable.',
    },
    {
      model: 'z-ai/glm-5.3-flash',
      result: '3 / 18 passed',
      passRate: '16.67%',
      citationRecall: '16.67%',
      judge: '100% over 14 judge labels',
      cost: '$0.011564736',
      status: 'limited-pass',
      note: 'Completed through NextBit; judge agreement does not change the low primary pass rate.',
    },
  ]
  const providerDiagnostics = [
    ['deepseek/deepseek-v4-flash-0731', 'DeepInfra', '4 / 18', '7 answered; 4 insufficient; 1 malformed; 5 unavailable; 1 timeout', '$0.003003420'],
    ['z-ai/glm-5.3-flash', 'NextBit', '3 / 18', '11 answered; 3 insufficient; 4 malformed', '$0.011564736'],
  ]
  const excludedCandidates = [
    ['tencent/hy3', 'DeepInfra / Tencent', 'Timed out through DeepInfra; unavailable through Tencent under the required privacy and no-fallback policy.'],
    ['xiaomi/mimo-v2.5', 'DeepInfra / Xiaomi', 'DeepInfra returned contract-invalid output; Xiaomi was unavailable under the required policy.'],
  ]
  const testEvidence = [
    ['Publication', '267 text files passed publication checks'],
    ['Metadata', 'JSON, Markdown links, action pins, story controls, and product versions passed'],
    ['API', '213 passed, 15 deselected'],
    ['Web unit', '36 passed'],
    ['E2E', '7 Playwright tests passed'],
    ['Build', 'Production Vite build passed'],
  ]
  const steps = [
    ['Source snapshot', '11 Kubernetes website Markdown files pinned at commit aa4e9e6dee49106155072a44ef997b91722243ec under CC BY 4.0.'],
    ['Normalize and hash', 'Files are UTF-8, NFC-normalized, LF-only, and checked against data/manifests/kubernetes-debug-cluster-v1.json.'],
    ['Chunk and index', 'Markdown is converted into 75 H2/H3 evidence sections, with long sections split only at paragraph boundaries.'],
    ['Review cases', '18 EvalGate-authored questions cover answerable, cross-document, terminology, outdated-assumption, and unanswerable behavior.'],
    ['Compare models', 'Three approved OpenRouter models completed the same 18-case contract with the same corpus, index, prompt policy, schema, temperature, no fallback, and privacy routing request.'],
  ]
  return <><header className="page-header"><p className="eyebrow">Real-world showcase</p><h1>Kubernetes debug documentation, governed end to end.</h1><p>This is the proof room for EG-018: source provenance, Markdown-to-evidence transformation, reviewed questions, model results, cost, tests, and limitations in one place.</p></header><section className="showcase-grid" aria-label="Kubernetes showcase summary"><article className="panel"><p className="eyebrow">Pinned source</p><h2>Kubernetes debug cluster docs</h2><dl className="identity-grid"><div><dt>Corpus</dt><dd>Kubernetes Debug Cluster</dd></div><div><dt>Version</dt><dd>1.0.0</dd></div><div><dt>Documents</dt><dd>11 Markdown files</dd></div><div><dt>Evidence chunks</dt><dd>75 reviewed sections</dd></div><div><dt>License</dt><dd>CC BY 4.0</dd></div><div><dt>Dataset</dt><dd>18 reviewed cases</dd></div><div><dt>Live runs</dt><dd>3 comparable models</dd></div><div><dt>Total reported cost</dt><dd>$0.019973359</dd></div></dl></article><article className="panel notice"><p className="eyebrow">Honest result</p><h2>The broken comparison was repaired.</h2><p>Stale model price ceilings left OpenRouter with no eligible route. After correction, three models completed the same 18-case contract; all remain below a production-quality threshold.</p><p>This page is not a public benchmark, deployment claim, or "best model" recommendation. The conclusion is that the workbench exposed weak and unstable results, not that a winner is ready for release.</p></article></section><section className="panel evidence-room" aria-labelledby="model-results-heading"><div className="section-heading"><div><p className="eyebrow">Live comparison</p><h2 id="model-results-heading">Model results and cost</h2></div><span className="tag tag--blue">OpenRouter / no fallback / ZDR requested</span></div><div className="table-wrap"><table className="evidence-table"><thead><tr><th>Model</th><th>Result</th><th>Pass rate</th><th>Citation recall</th><th>Judge evidence</th><th>Cost</th></tr></thead><tbody>{modelResults.map((row) => <tr key={row.model}><td><code>{row.model}</code><p>{row.note}</p></td><td><span className={row.status === 'failed' ? 'tag tag--red' : 'tag tag--yellow'}>{row.result}</span></td><td>{row.passRate}</td><td>{row.citationRecall}</td><td>{row.judge}</td><td><strong>{row.cost}</strong></td></tr>)}</tbody></table></div></section><section className="panel evidence-room" aria-labelledby="provider-diagnostics-heading"><div className="section-heading"><div><p className="eyebrow">Provider diagnostics</p><h2 id="provider-diagnostics-heading">Provider-pinned reruns</h2></div><span className="tag tag--green">Routing defect repaired</span></div><div className="table-wrap"><table className="evidence-table"><thead><tr><th>Model</th><th>Provider</th><th>Result</th><th>Status summary</th><th>Cost</th></tr></thead><tbody>{providerDiagnostics.map(([model, provider, result, status, cost]) => <tr key={`${model}-${provider}`}><td><code>{model}</code></td><td>{provider}</td><td>{result}</td><td>{status}</td><td><strong>{cost}</strong></td></tr>)}</tbody></table></div><div className="stalled-grid" aria-label="Excluded candidate diagnostics">{excludedCandidates.map(([model, route, note]) => <article className="test-card" key={model}><strong>{model}</strong><span>{route}</span><span>{note}</span></article>)}</div></section><section className="diagnosis-grid" aria-label="Model result diagnosis"><article className="panel"><p className="eyebrow">Why so low?</p><h2>This is not a win/loss leaderboard yet.</h2><p>The original zero-cost failures came from stale <code>max_price</code> ceilings, not model quality. Repaired runs reached inference and exposed the real mix of weak answers, citation misses, malformed output, timeouts, and intermittent provider availability.</p></article><article className="panel"><p className="eyebrow">Bias check</p><h2>Not benchmarked to the first model.</h2><p>All approved candidates used the same corpus, index, dataset, prompt hash, output schema, temperature, retrieval limit, privacy request, and budget rule. The comparison may still be too strict or immature, but it is not tuned per model or secretly optimized for one candidate.</p></article></section><section className="showcase-grid" aria-label="Markdown evidence presentation"><article className="panel"><p className="eyebrow">Markdown as evidence</p><h2>Files become readable evidence sections.</h2><p>EvalGate does not ask users to trust raw Markdown filenames. The source files are normalized, hashed, split into section-level chunks, indexed, and then cited back as retrieved evidence with document title, section, checksum, and technical identifiers available on demand.</p><div className="source-card-grid">{sourceFiles.map(([file, title]) => <article className="source-card" key={file}><span className="file-icon" aria-hidden="true">md</span><div><h3>{title}</h3><p><code>{file}</code></p></div></article>)}</div></article><article className="panel"><p className="eyebrow">Review set</p><h2>18 questions before any model call.</h2><p>The Kubernetes cases were authored and reviewed before the live run. They include normal answerable questions, cross-document questions, outdated assumptions, and unanswerable cases so failures are meaningful.</p><ul className="evidence-list"><li>Same corpus and index for every model.</li><li>Same prompt policy and JSON schema.</li><li>Same temperature and one current comparable repetition per case.</li><li>No provider fallback or browser secret.</li></ul></article></section><section className="flow showcase-flow" aria-labelledby="showcase-flow-heading"><p className="eyebrow">Under the hood</p><h2 id="showcase-flow-heading">How the example works</h2><ol>{steps.map(([title, detail], index) => <li key={title}><strong>{index + 1}. {title}</strong><span>{detail}</span></li>)}</ol></section><section className="panel evidence-room" aria-labelledby="test-evidence-heading"><div className="section-heading"><div><p className="eyebrow">Verification</p><h2 id="test-evidence-heading">Tests that back this local view</h2></div><span className="tag tag--green">0.11.0 verified locally + rerun reported</span></div><div className="test-grid">{testEvidence.map(([name, detail]) => <article className="test-card" key={name}><strong>{name}</strong><span>{detail}</span></article>)}</div><details><summary>Artifact and review files</summary><dl className="technical-list"><div><dt>Live summary</dt><dd><code>docs/evaluation/EG-018-live-comparison.md</code></dd></div><div><dt>Dataset</dt><dd><code>contracts/evaluation/kubernetes-debug-v1.json</code></dd></div><div><dt>Source manifest</dt><dd><code>data/manifests/kubernetes-debug-cluster-v1.json</code></dd></div><div><dt>Review records</dt><dd><code>docs/evaluation/reviews/kubernetes-v1-openrouter-*.json</code></dd></div></dl></details></section><section className="panel"><p className="eyebrow">Attribution</p><h2>Source and endorsement boundary</h2><p>Kubernetes documentation is attributed to The Kubernetes Authors and licensed under CC BY 4.0. Kubernetes is a trademark of The Linux Foundation. EvalGate is not endorsed by or affiliated with Kubernetes, CNCF, or The Linux Foundation.</p><details><summary>Technical details</summary><dl className="technical-list"><div><dt>Upstream repository</dt><dd><code>https://github.com/kubernetes/website</code></dd></div><div><dt>Approved path</dt><dd><code>content/en/docs/tasks/debug/debug-cluster/</code></dd></div><div><dt>Chunking policy</dt><dd><code>kubernetes-debug-heading-v1</code></dd></div><div><dt>Provider policy</dt><dd><code>zdr=true, data_collection=deny, allow_fallbacks=false</code></dd></div></dl></details></section></>
}
function SystemEvidence({ catalog, selected, catalogError }: Readonly<{ catalog: readonly InspectionCatalogItem[] | null; selected: InspectionCatalogItem | null; catalogError: boolean }>) {
  return <><header className="page-header"><p className="eyebrow">System evidence</p><h1>See what this local workbench is using.</h1><p>Names come first. Immutable identifiers remain available for reproduction and audit.</p></header><section className="panel"><h2>Current inspection source</h2>{catalog === null ? <p role="status">Loading source identity</p> : null}{catalogError ? <p className="result-error">Source identity is unavailable while the catalog cannot be reached.</p> : null}{selected ? <><dl className="identity-grid"><div><dt>Corpus</dt><dd>{contentText(titleCase(selected.corpus_key))}</dd></div><div><dt>Corpus version</dt><dd>{contentText(selected.corpus_version)}</dd></div><div><dt>Index policy</dt><dd>{contentText(titleCase(selected.index_key))}</dd></div><div><dt>Browser mode</dt><dd>Deterministic fixture</dd></div></dl><details><summary>Technical details</summary><dl className="technical-list"><div><dt>Index version ID</dt><dd><code>{contentText(selected.index_version)}</code></dd></div><div><dt>Corpus key</dt><dd><code>{contentText(selected.corpus_key)}</code></dd></div></dl></details></> : null}</section></>
}
