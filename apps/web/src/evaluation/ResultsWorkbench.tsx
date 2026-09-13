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
import { contentText } from '../presentation/safeContent'

function label(key: string): string {
  return key.replaceAll('_', ' ')
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

type LoadedResult = Readonly<{ detail: EvaluationRunDetail; cases: readonly EvaluationCase[] }>

export function ResultsWorkbench() {
  const [runs, setRuns] = useState<readonly EvaluationRun[] | null>(null)
  const [selectedRun, setSelectedRun] = useState('')
  const [compareTo, setCompareTo] = useState('')
  const [caseStatus, setCaseStatus] = useState<CaseStatus | ''>('')
  const [result, setResult] = useState<LoadedResult | null>(null)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)
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
      .then(([detail, cases]) => setResult({ detail, cases: cases.items }))
      .catch(() => {
        if (!controller.signal.aborted) setError(true)
      })
    return () => controller.abort()
  }, [caseStatus, compareTo, revision, selectedRun])

  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])

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
        <p className="muted">No reviewed evaluation runs are available.</p>
      ) : null}
      {runs && runs.length > 0 ? (
        <>
          <div className="result-controls">
            <label htmlFor="evaluation-run">Run</label>
            <select
              id="evaluation-run"
              value={selectedRun}
              onChange={(event) => {
                setSelectedRun(event.target.value)
                setCompareTo('')
                setResult(null)
                setError(false)
              }}
            >
              {runs.map((run) => <option key={run.run_key} value={run.run_key}>{run.run_key}</option>)}
            </select>
            <label htmlFor="comparison-run">Compare metrics with</label>
            <select id="comparison-run" value={compareTo} onChange={(event) => { setCompareTo(event.target.value); setResult(null); setError(false) }}>
              <option value="">No comparison</option>
              {runs.filter((run) => run.run_key !== selectedRun).map((run) => (
                <option key={run.run_key} value={run.run_key}>{run.run_key}</option>
              ))}
            </select>
          </div>
          {!detail && !error ? <p role="status" aria-atomic="true">Loading run details...</p> : null}
          {detail ? (
            <>
              <div className="result-summary">
                <div><span className="status-badge">{detail.status}</span><p>{detail.mode} mode</p></div>
                <dl className="identity-grid">
                  <div><dt>Code SHA</dt><dd><code>{detail.code_sha}</code></dd></div>
                  <div><dt>Artifact SHA-256</dt><dd><code>{detail.artifact_sha256}</code></dd></div>
                  <div><dt>Index</dt><dd>{contentText(identity(detail.versions.index_key))}</dd></div>
                  <div><dt>Dataset SHA-256</dt><dd><code>{identity(detail.versions.dataset_manifest_sha256)}</code></dd></div>
                  <div><dt>Corpus SHA-256</dt><dd><code>{identity(detail.versions.corpus_manifest_sha256)}</code></dd></div>
                  <div><dt>Policy</dt><dd>{contentText(identity(detail.versions.policy_version))}</dd></div>
                </dl>
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
                    <label htmlFor="case-status">Status</label>
                    <select id="case-status" value={caseStatus} onChange={(event) => { setCaseStatus(event.target.value as CaseStatus | ''); setResult(null); setError(false) }}>
                      <option value="">All cases</option>
                      <option value="failed">Failed only</option>
                      <option value="passed">Passed only</option>
                    </select>
                  </div>
                </div>
                {result.cases.length === 0 ? <p className="muted">No cases match this status.</p> : (
                  <div className="case-list">
                    {result.cases.map((item) => (
                      <article className={`result-case result-case--${item.status}`} key={item.case_id}>
                        <div className="case-title"><h4>{item.case_id}: {item.question}</h4><span>{item.status}</span></div>
                        <p className="muted">{item.split} · {item.answerable ? 'answerable' : 'unanswerable'}</p>
                        <p><strong>Retrieved evidence</strong></p>
                        {item.retrieved_evidence_ids.length > 0 ? (
                          <ul className="evidence-ids">{item.retrieved_evidence_ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul>
                        ) : <p className="muted">No evidence retrieved.</p>}
                        <p><strong>Reviewed relevant evidence</strong></p>
                        {item.relevant_evidence_ids.length > 0 ? (
                          <ul className="evidence-ids">{item.relevant_evidence_ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul>
                        ) : <p className="muted">No relevant evidence expected.</p>}
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
