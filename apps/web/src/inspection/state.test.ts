import { describe, expect, it } from 'vitest'
import { initialInspectionState, inspectionReducer } from './state'
import type { AnswerStreamEventType } from '../api/answerStream'

const request = { question: 'Q', index_version: 'fixture-v1', mode: 'fixture' as const }
const event = (type: AnswerStreamEventType, sequence: number, extra: Record<string, unknown> = {}) => ({ schema_version: '1.0' as const, request_id: 'r', sequence, type, ...extra })

describe('inspection reducer protocol guard', () => {
  it('advances through lifecycle and keeps answer text', () => {
    let state = inspectionReducer(initialInspectionState, { type: 'submit', request })
    state = inspectionReducer(state, { type: 'stream_event', event: event('answer.started', 1, { prompt_policy: { id: 'p', version: '1', sha256: 'h' } }) })
    state = inspectionReducer(state, { type: 'stream_event', event: event('retrieval.completed', 2, { index_version: 'i', corpus_version: 'c', evidence_ids: [] }) })
    state = inspectionReducer(state, { type: 'stream_event', event: event('answer.delta', 3, { text: 'A' }) })
    expect(state.answer).toBe('A')
  })

  it('rejects duplicate or out-of-order events', () => {
    let state = inspectionReducer(initialInspectionState, { type: 'submit', request })
    state = inspectionReducer(state, { type: 'stream_event', event: event('answer.started', 2, { prompt_policy: { id: 'p', version: '1', sha256: 'h' } }) })
    expect(state.phase).toBe('failed')
    expect(state.errorCode).toBe('protocol.sequence')
  })

  it('does not expose provider error details', () => {
    let state = inspectionReducer(initialInspectionState, { type: 'submit', request })
    state = inspectionReducer(state, { type: 'stream_event', event: event('answer.started', 1, { prompt_policy: { id: 'p', version: '1', sha256: 'h' } }) })
    state = inspectionReducer(state, { type: 'stream_event', event: event('answer.failed', 2, { code: 'provider.secret' }) })
    expect(state.phase).toBe('failed')
    expect(state.errorMessage).not.toContain('secret')
  })

  it('cancels only active requests', () => {
    const idle = inspectionReducer(initialInspectionState, { type: 'cancel' })
    expect(idle.phase).toBe('idle')
    const active = inspectionReducer(initialInspectionState, { type: 'submit', request })
    expect(inspectionReducer(active, { type: 'cancel' }).phase).toBe('cancelled')
  })
})
