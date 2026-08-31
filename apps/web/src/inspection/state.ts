import type { AnswerStreamEvent, AnswerStreamEventType, AskRequest } from '../api/answerStream'

export type InspectionPhase =
  | 'idle'
  | 'submitting'
  | 'retrieving'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type SearchEvidence = Readonly<{
  rank: number
  evidence_id: string
  document_id: string
  source_key: string
  title: string
  license_id: string
  provenance: string
  section_key: string
  source_start: number
  source_end: number
  content: string
  content_sha256: string
  lexical_rank: number | null
  vector_rank: number | null
  rrf_score: number
}>

export type Citation = Readonly<{
  answer_start: number
  answer_end: number
  claim: string
  evidence_id: string
  document_id: string
  source_key: string
  title: string
  license_id: string
  provenance: string
  section_key: string
  source_start: number
  source_end: number
  span_sha256: string
  quote: string
}>

export type InspectionState = Readonly<{
  phase: InspectionPhase
  request: AskRequest | null
  requestId: string | null
  expectedSequence: number
  answer: string
  answerStatus: string | null
  citations: Citation[]
  citationsReady: boolean
  evidence: SearchEvidence[]
  indexVersion: string | null
  corpusVersion: string | null
  promptPolicy: Readonly<{ id: string; version: string; sha256: string }> | null
  provider: Readonly<{ mode: string; name: string; revision: string }> | null
  errorCode: string | null
  errorMessage: string | null
}>

export type InspectionAction =
  | { type: 'submit'; request: AskRequest }
  | { type: 'stream_event'; event: AnswerStreamEvent }
  | { type: 'evidence_loaded'; evidence: SearchEvidence[] }
  | { type: 'evidence_failed' }
  | { type: 'transport_failed'; code: string }
  | { type: 'cancel' }
  | { type: 'reset' }

export const initialInspectionState: InspectionState = {
  phase: 'idle',
  request: null,
  requestId: null,
  expectedSequence: 1,
  answer: '',
  answerStatus: null,
  citations: [],
  citationsReady: false,
  evidence: [],
  indexVersion: null,
  corpusVersion: null,
  promptPolicy: null,
  provider: null,
  errorCode: null,
  errorMessage: null,
}

const failure = (state: InspectionState, code: string, message: string): InspectionState => ({
  ...state,
  phase: 'failed',
  errorCode: code,
  errorMessage: message,
})

function stringValue(event: AnswerStreamEvent, key: string): string | null {
  const value = event[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function eventType(event: AnswerStreamEvent): AnswerStreamEventType {
  return event.type
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? value as Record<string, unknown> : null
}

export function inspectionReducer(
  state: InspectionState,
  action: InspectionAction,
): InspectionState {
  if (action.type === 'reset') return initialInspectionState
  if (action.type === 'submit') {
    return {
      ...initialInspectionState,
      phase: 'submitting',
      request: action.request,
    }
  }
  if (action.type === 'evidence_loaded') return { ...state, evidence: action.evidence }
  if (action.type === 'evidence_failed') return { ...state, evidence: [] }
  if (action.type === 'transport_failed') {
    return failure(state, action.code, 'The answer could not be loaded. Please try again.')
  }
  if (action.type === 'cancel') {
    return state.phase === 'submitting' || state.phase === 'retrieving' || state.phase === 'streaming'
      ? { ...state, phase: 'cancelled', errorCode: 'stream.cancelled', errorMessage: null }
      : state
  }

  const event = action.event
  if (state.phase === 'completed' || state.phase === 'failed' || state.phase === 'cancelled') {
    return failure(state, 'protocol.terminal', 'The stream sent data after it ended.')
  }
  if (event.sequence !== state.expectedSequence) {
    return failure(state, 'protocol.sequence', 'The stream order could not be verified.')
  }
  if (state.requestId !== null && event.request_id !== state.requestId) {
    return failure(state, 'protocol.request', 'The stream request identity changed unexpectedly.')
  }

  const next = { ...state, expectedSequence: state.expectedSequence + 1 }
  switch (eventType(event)) {
    case 'answer.started': {
      if (state.phase !== 'submitting' || state.requestId !== null) {
        return failure(state, 'protocol.lifecycle', 'The stream started in an invalid state.')
      }
      const policy = recordValue(event.prompt_policy)
      if (
        typeof policy !== 'object' ||
        policy === null ||
        typeof policy.id !== 'string' ||
        typeof policy.version !== 'string' ||
        typeof policy.sha256 !== 'string'
      ) {
        return failure(state, 'protocol.data', 'The stream metadata is invalid.')
      }
      return {
        ...next,
        phase: 'retrieving',
        requestId: event.request_id,
        promptPolicy: { id: policy.id, version: policy.version, sha256: policy.sha256 },
      }
    }
    case 'retrieval.completed': {
      if (state.phase !== 'retrieving') {
        return failure(state, 'protocol.lifecycle', 'Retrieval completed in an invalid state.')
      }
      const indexVersion = stringValue(event, 'index_version')
      const corpusVersion = stringValue(event, 'corpus_version')
      if (indexVersion === null || corpusVersion === null || !Array.isArray(event.evidence_ids)) {
        return failure(state, 'protocol.data', 'The retrieval metadata is invalid.')
      }
      return { ...next, phase: 'streaming', indexVersion, corpusVersion }
    }
    case 'answer.delta': {
      if (state.phase !== 'streaming' || typeof event.text !== 'string' || event.text.length === 0) {
        return failure(state, 'protocol.data', 'The answer delta is invalid.')
      }
      return { ...next, answer: state.answer + event.text }
    }
    case 'citations.completed': {
      if (state.phase !== 'streaming' || !Array.isArray(event.citations)) {
        return failure(state, 'protocol.data', 'The citation payload is invalid.')
      }
      return { ...next, citations: event.citations as Citation[], citationsReady: true }
    }
    case 'answer.completed': {
      if (state.phase !== 'streaming') {
        return failure(state, 'protocol.lifecycle', 'The answer completed in an invalid state.')
      }
      const status = stringValue(event, 'status')
      const provider = recordValue(event.provider)
      if (
        status === null ||
        typeof provider !== 'object' ||
        provider === null ||
        typeof provider.mode !== 'string' ||
        typeof provider.name !== 'string' ||
        typeof provider.revision !== 'string'
      ) {
        return failure(state, 'protocol.data', 'The completion payload is invalid.')
      }
      return {
        ...next,
        phase: 'completed',
        answerStatus: status,
        provider: { mode: provider.mode, name: provider.name, revision: provider.revision },
      }
    }
    case 'answer.failed':
      return {
        ...next,
        phase: 'failed',
        errorCode: stringValue(event, 'code') ?? 'provider.failed',
        errorMessage: 'The answer provider could not complete this request.',
      }
    case 'answer.cancelled':
      return { ...next, phase: 'cancelled', errorCode: 'stream.cancelled', errorMessage: null }
  }
}
