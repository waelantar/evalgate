import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchEvaluationCases,
  fetchEvaluationRun,
  fetchEvaluationRuns,
  type CaseStatus,
  type EvaluationCase,
  type EvaluationRun,
  type EvaluationRunDetail,
} from '../api/evaluationRuns'
import { Picker } from '../components/Picker'
import { contentText } from '../presentation/safeContent'

function label(key: string): string {
  return key.replaceAll('_', ' ')
}

function runLabel(runKey: string): string {
  return `Evaluation - ${label(runKey)}`
}

function metricValue(key: string, value: number): string {
  return key === 'case_count' ? String(value) : `${(value * 100).toFixed(1)}%`
}

function deltaValue(key: string, value: number): string {
  if (key === 'case_count') return `${value >= 0 ? '+' : ''}${value}`
  const points = value * 100
  return `${points >= 0 ? '+' : ''}${points.toFixed(1)} pp`
}

function identity(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : 'not recorded'
}

const NO_COMPARISON = '__no-comparison'
const ALL_CASES = '__all-cases'

type LoadedResult = Readonly<{ detail: EvaluationRunDetail; cases: readonly EvaluationCase[]; nextCaseCursor: string | null }>

export function ResultsWorkbench() {
  const [runs, setRuns] = useState<readonly EvaluationRun[] | null>(null)
  const [selectedRun, setSelectedRun] = useState('')
  const [compareTo, setCompareTo] = useState('')
  const [caseStatus, setCaseStatus] = useState<CaseStatus | ''>('')
  const [result, setResult] = useState<LoadedResult | null>(null)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const errorRef = useRef<HTMLDivElement | null>(null)

  const retry = useCallback(() => {
    setError(false)
    setRuns(null)
    setResult(null)
    setRevision((value) => value + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void fetchEvaluationRuns(controller.signal)
      .then((page) => {
        setRuns(page.items)
        setSelectedRun((current) => current || page.items[0]?.run_key || '')
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setRuns([])
          setError(true)
        }
      })
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    if (!selectedRun) return
    const controller = new AbortController()
    void Promise.all([
      fetchEvaluationRun(selectedRun, compareTo || null, controller.signal),
      fetchEvaluationCases(selectedRun, caseStatus || null, controller.signal),
    ])
      .then(([detail, cases]) => setResult({ detail, cases: cases.items, nextCaseCursor: cases.next_cursor }))
      .catch(() => {
        if (!controller.signal.aborted) setError(true)
      })
    return () => controller.abort()
  }, [caseStatus, compareTo, revision, selectedRun])

  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])

  function loadMoreCases() {
    if (!selectedRun || result === null || result.nextCaseCursor === null || loadingMore) return
    setLoadingMore(true)
    void fetchEvaluationCases(selectedRun, caseStatus || null, undefined, result.nextCaseCursor)
      .then((page) => setResult((current) => current === null ? null : { ...current, cases: [...current.cases, ...page.items], nextCaseCursor: page.next_cursor }))
      .catch(() => setError(true))
      .finally(() => setLoadingMore(false))
  }
  const detail = result?.detail
  return (
    <section className="panel results-panel" aria-labelledby="runs-heading">
      <p className="eyebrow">Read-only evaluation evidence</p>
      <h2 id="runs-heading">Evaluation results</h2>
      {runs === null && !error ? <p role="status" aria-atomic="true">Loading evaluation runs...</p> : null}
      {error ? (
        <div ref={errorRef} role="alert" className="result-error" tabIndex={-1}>
          <p>Evaluation results could not be loaded.</p>
          <button type="button" className="secondary compact" onClick={retry}>Retry</button>
        </div>
      ) : null}
      {runs?.length === 0 && !error ? (
        <div className="empty-state"><img src="/evalgate-mark.svg" alt="" /><p className="muted">No reviewed evaluation runs are available.</p></div>
      ) : null}
      {runs && runs.length > 0 ? (
        <>
          <div className="result-controls">
            <Picker id="evaluation-run" label="Run" value={selectedRun} onChange={(value) => { setSelectedRun(value); setCompareTo(''); setResult(null); setError(false) }} options={runs.map((run) => ({ value: run.run_key, label: runLabel(run.run_key) }))} />
            <Picker id="comparison-run" label="Compare metrics with" value={compareTo || NO_COMPARISON} onChange={(value) => { setCompareTo(value === NO_COMPARISON ? '' : value); setResult(null); setError(false) }} options={[{ value: NO_COMPARISON, label: 'No comparison' }, ...runs.filter((run) => run.run_key !== selectedRun).map((run) => ({ value: run.run_key, label: runLabel(run.run_key) }))]} />
          </div>
          {!detail && !error ? <p role="status" aria-atomic="true">Loading run details...</p> : null}
          {detail ? (
            <>
              <div className="result-summary">
                <div><span className="status-badge">{detail.status}</span><p>{detail.mode} evaluation</p></div>
                <dl className="identity-grid">
                  <div><dt>Index</dt><dd>{contentText(identity(detail.versions.index_key))}</dd></div>
                  <div><dt>Policy</dt><dd>{contentText(identity(detail.versions.policy_version))}</dd></div>
                </dl>
                <details><summary>Technical details</summary><dl className="technical-list"><div><dt>Code checksum</dt><dd><code>{detail.code_sha}</code></dd></div><div><dt>Artifact checksum</dt><dd><code>{detail.artifact_sha256}</code></dd></div><div><dt>Dataset checksum</dt><dd><code>{identity(detail.versions.dataset_manifest_sha256)}</code></dd></div><div><dt>Corpus checksum</dt><dd><code>{identity(detail.versions.corpus_manifest_sha256)}</code></dd></div></dl></details>
              </div>
              <section aria-labelledby="metrics-heading">
                <h3 id="metrics-heading">Metrics</h3>
                <dl className="metrics-grid">
                  {Object.entries(detail.metrics).map(([key, value]) => (
                    <div key={key}>
                      <dt>{contentText(label(key))}</dt>
                      <dd>{metricValue(key, value)}</dd>
                      {detail.metric_deltas?.[key] !== undefined ? (
                        <small>{deltaValue(key, detail.metric_deltas[key])} vs {contentText(detail.comparison_run_key ?? 'the selected comparison')}</small>
                      ) : null}
                    </div>
                  ))}
                </dl>
              </section>
              <section aria-labelledby="limitations-heading">
                <h3 id="limitations-heading">Limitations</h3>
                <ul>{detail.limitations.map((item) => <li key={item}>{contentText(item)}</li>)}</ul>
              </section>
              <section aria-labelledby="cases-heading">
                <div className="case-heading">
                  <h3 id="cases-heading">Case evidence</h3>
                  <div>
                    <Picker id="case-status" label="Status" value={caseStatus || ALL_CASES} onChange={(value) => { setCaseStatus(value === ALL_CASES ? '' : value as CaseStatus); setResult(null); setError(false) }} options={[{ value: ALL_CASES, label: 'All cases' }, { value: 'failed', label: 'Failed only' }, { value: 'passed', label: 'Passed only' }]} />
                  </div>
                </div>
                {result.cases.length === 0 ? <p className="muted">No cases match this status.</p> : (
                  <div className="case-list">
                    {result.cases.map((item) => (
                      <article className={`result-case result-case--${item.status}`} key={item.case_id}>
                        <div className="case-title"><h4>{item.case_id}: {item.question}</h4><span>{item.status}</span></div>
                        <p className="muted">{item.split} / {item.answerable ? 'answerable' : 'unanswerable'}</p>
                        <p><strong>Retrieved evidence</strong> / {item.retrieved_evidence_ids.length} passage{item.retrieved_evidence_ids.length === 1 ? '' : 's'}</p>
                        {item.retrieved_evidence_ids.length > 0 ? (
                          <details><summary>Technical evidence IDs</summary><ul className="evidence-ids">{item.retrieved_evidence_ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul></details>
                        ) : <p className="muted">No evidence retrieved.</p>}
                        <p><strong>Reviewed relevant evidence</strong> / {item.relevant_evidence_ids.length} expected passage{item.relevant_evidence_ids.length === 1 ? '' : 's'}</p>
                        {item.relevant_evidence_ids.length > 0 ? (
                          <details><summary>Technical evidence IDs</summary><ul className="evidence-ids">{item.relevant_evidence_ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul></details>
                        ) : <p className="muted">No relevant evidence expected.</p>}
                      </article>
                    ))}
                  </div>
                )}
                {result.nextCaseCursor !== null ? <nav className="case-pagination" aria-label="Case pagination"><span className="muted">Showing {result.cases.length} reviewed cases</span><button type="button" className="secondary compact" onClick={loadMoreCases} disabled={loadingMore}>{loadingMore ? 'Loading cases...' : 'Show more cases'}</button></nav> : null}
              </section>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
