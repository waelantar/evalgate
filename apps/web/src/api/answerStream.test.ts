import { describe, expect, it, vi } from 'vitest'

import {
  AnswerStreamParser,
  AnswerStreamProtocolError,
  fetchAnswerStream,
} from './answerStream'

const encoder = new TextEncoder()
const requestId = '50000000-0000-0000-0000-000000000001'

function frame(type: string, sequence: number, extra: Record<string, unknown> = {}): string {
  return `event: ${type}\nid: ${sequence}\ndata: ${JSON.stringify({ schema_version: '1.0', request_id: requestId, sequence, type, ...extra })}\n\n`
}

function completeStream(answer = 'résumé ✅'): string {
  return (
    frame('answer.started', 1) +
    ': heartbeat\n\n' +
    frame('retrieval.completed', 2) +
    frame('answer.delta', 3, { text: answer }) +
    frame('citations.completed', 4, { citations: [] }) +
    frame('answer.completed', 5, { status: 'answered' })
  )
}

describe('AnswerStreamParser', () => {
  it('preserves split UTF-8 code points, partial frames, multiple frames, and heartbeats', () => {
    const bytes = encoder.encode(completeStream())
    const emoji = encoder.encode('✅')
    const emojiStart = bytes.findIndex((_value, index) =>
      emoji.every((part, offset) => bytes[index + offset] === part),
    )
    const parser = new AnswerStreamParser()
    const events = [
      ...parser.push(bytes.slice(0, 17)),
      ...parser.push(bytes.slice(17, emojiStart + 1)),
      ...parser.push(bytes.slice(emojiStart + 1)),
      ...parser.finish(),
    ]

    expect(events.map((event) => event.type)).toEqual([
      'answer.started',
      'retrieval.completed',
      'answer.delta',
      'citations.completed',
      'answer.completed',
    ])
    expect(events[2]?.text).toBe('résumé ✅')
  })

  it.each([
    ['malformed JSON', 'event: answer.started\nid: 1\ndata: {\n\n'],
    ['non-object JSON', 'event: answer.started\nid: 1\ndata: []\n\n'],
    ['unknown version', frame('answer.started', 1).replace('"1.0"', '"2.0"')],
    ['unknown event', frame('answer.unknown', 1)],
    ['frame/data mismatch', frame('answer.started', 1).replace('"answer.started"', '"answer.delta"')],
    ['id/data mismatch', frame('answer.started', 1).replace('"sequence":1', '"sequence":2')],
    ['extra line', frame('answer.started', 1).replace('data: ', 'retry: 1\ndata: ')],
    ['invalid field', frame('answer.started', 1).replace('event: ', 'event! ')],
  ])('rejects %s', (_label, value) => {
    const parser = new AnswerStreamParser()
    expect(() => parser.push(encoder.encode(value))).toThrow(AnswerStreamProtocolError)
  })

  it.each([
    ['duplicate', frame('answer.started', 1) + frame('retrieval.completed', 1)],
    ['out of order', frame('answer.started', 1) + frame('retrieval.completed', 3)],
    ['after terminal', frame('answer.failed', 1) + frame('answer.delta', 2)],
  ])('rejects %s sequencing', (_label, value) => {
    const parser = new AnswerStreamParser()
    expect(() => parser.push(encoder.encode(value))).toThrow(AnswerStreamProtocolError)
  })

  it('rejects partial and non-terminal stream endings', () => {
    const partial = new AnswerStreamParser()
    partial.push(encoder.encode('event: answer.started'))
    expect(() => partial.finish()).toThrow('partial SSE frame')

    const nonTerminal = new AnswerStreamParser()
    nonTerminal.push(encoder.encode(frame('answer.started', 1)))
    expect(() => nonTerminal.finish()).toThrow('stream ended without a terminal event')
  })

  it('rejects bytes supplied after a terminal frame', () => {
    const parser = new AnswerStreamParser()
    parser.push(encoder.encode(frame('answer.failed', 1)))
    expect(() => parser.push(encoder.encode(': heartbeat\n\n'))).toThrow(
      'data followed the terminal event',
    )
  })

  it('rejects invalid and incomplete UTF-8', () => {
    const invalid = new AnswerStreamParser()
    expect(() => invalid.push(new Uint8Array([0xff]))).toThrow('invalid UTF-8 stream')

    const incomplete = new AnswerStreamParser()
    incomplete.push(new Uint8Array([0xe2]))
    expect(() => incomplete.finish()).toThrow('invalid UTF-8 stream')
  })
})

describe('fetchAnswerStream', () => {
  it('passes AbortSignal to fetch and consumes the UTF-8 stream', async () => {
    const controller = new AbortController()
    const body = new ReadableStream<Uint8Array>({
      start(streamController) {
        streamController.enqueue(encoder.encode(completeStream('bounded')))
        streamController.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const events = []
    for await (const event of fetchAnswerStream(
      { question: 'question', index_version: requestId, mode: 'fixture' },
      controller.signal,
    )) {
      events.push(event)
    }

    expect(events).toHaveLength(5)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/ask',
      expect.objectContaining({ signal: controller.signal }),
    )
    vi.unstubAllGlobals()
  })

  it.each([
    [new Response(null, { status: 503 }), 'ask failed before stream: 503'],
    [
      new Response('json', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      'not an event stream',
    ],
    [
      new Response(null, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
      'no body',
    ],
  ])('rejects invalid pre-stream response %#', async (response, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    const consume = async () => {
      for await (const event of fetchAnswerStream(
        { question: 'question', index_version: requestId, mode: 'fixture' },
        new AbortController().signal,
      )) {
        void event
      }
    }
    await expect(consume()).rejects.toThrow(message)
    vi.unstubAllGlobals()
  })
})
