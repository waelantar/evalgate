export const ANSWER_STREAM_SCHEMA_VERSION = '1.0' as const

export type AnswerStreamEventType =
  | 'answer.started'
  | 'retrieval.completed'
  | 'answer.delta'
  | 'citations.completed'
  | 'answer.completed'
  | 'answer.failed'
  | 'answer.cancelled'

export type AnswerStreamEvent = Readonly<{
  schema_version: typeof ANSWER_STREAM_SCHEMA_VERSION
  request_id: string
  sequence: number
  type: AnswerStreamEventType
}> &
  Readonly<Record<string, unknown>>

const EVENT_TYPES = new Set<AnswerStreamEventType>([
  'answer.started',
  'retrieval.completed',
  'answer.delta',
  'citations.completed',
  'answer.completed',
  'answer.failed',
  'answer.cancelled',
])
const TERMINAL_TYPES = new Set<AnswerStreamEventType>([
  'answer.completed',
  'answer.failed',
  'answer.cancelled',
])

export class AnswerStreamProtocolError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AnswerStreamProtocolError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseFrame(frame: string): AnswerStreamEvent | null {
  const lines = frame.split('\n')
  if (lines.every((line) => line === '' || line.startsWith(':'))) return null
  if (lines.length !== 3) throw new AnswerStreamProtocolError('invalid SSE frame shape')

  const [eventLine, idLine, dataLine] = lines
  if (
    eventLine === undefined ||
    idLine === undefined ||
    dataLine === undefined ||
    !eventLine.startsWith('event: ') ||
    !idLine.startsWith('id: ') ||
    !dataLine.startsWith('data: ')
  ) {
    throw new AnswerStreamProtocolError('invalid SSE frame fields')
  }

  const eventName = eventLine.slice(7)
  const idText = idLine.slice(4)
  if (!EVENT_TYPES.has(eventName as AnswerStreamEventType) || !/^[1-9]\d*$/.test(idText)) {
    throw new AnswerStreamProtocolError('invalid SSE event identity')
  }

  let value: unknown
  try {
    value = JSON.parse(dataLine.slice(6))
  } catch {
    throw new AnswerStreamProtocolError('invalid SSE JSON')
  }
  if (!isRecord(value)) throw new AnswerStreamProtocolError('invalid SSE data object')

  const event = value as Partial<AnswerStreamEvent>
  const sequence = Number(idText)
  if (
    event.schema_version !== ANSWER_STREAM_SCHEMA_VERSION ||
    typeof event.request_id !== 'string' ||
    event.request_id.length === 0 ||
    event.sequence !== sequence ||
    event.type !== eventName
  ) {
    throw new AnswerStreamProtocolError('SSE envelope mismatch')
  }
  return event as AnswerStreamEvent
}

export class AnswerStreamParser {
  readonly #decoder = new TextDecoder('utf-8', { fatal: true })
  #buffer = ''
  #expectedSequence = 1
  #terminal = false

  push(chunk: Uint8Array): AnswerStreamEvent[] {
    if (this.#terminal && chunk.length > 0) {
      throw new AnswerStreamProtocolError('data followed the terminal event')
    }
    try {
      this.#buffer += this.#decoder.decode(chunk, { stream: true }).replaceAll('\r\n', '\n')
    } catch {
      throw new AnswerStreamProtocolError('invalid UTF-8 stream')
    }
    return this.#drain()
  }

  finish(): AnswerStreamEvent[] {
    try {
      this.#buffer += this.#decoder.decode()
    } catch {
      throw new AnswerStreamProtocolError('invalid UTF-8 stream')
    }
    const events = this.#drain()
    if (this.#buffer.length > 0) throw new AnswerStreamProtocolError('partial SSE frame')
    if (!this.#terminal) throw new AnswerStreamProtocolError('stream ended without a terminal event')
    return events
  }

  #drain(): AnswerStreamEvent[] {
    const events: AnswerStreamEvent[] = []
    for (;;) {
      const boundary = this.#buffer.indexOf('\n\n')
      if (boundary < 0) return events
      const frame = this.#buffer.slice(0, boundary)
      this.#buffer = this.#buffer.slice(boundary + 2)
      const event = parseFrame(frame)
      if (event === null) continue
      if (this.#terminal) throw new AnswerStreamProtocolError('event followed the terminal event')
      if (event.sequence !== this.#expectedSequence) {
        throw new AnswerStreamProtocolError('duplicate or out-of-order sequence')
      }
      this.#expectedSequence += 1
      this.#terminal = TERMINAL_TYPES.has(event.type)
      events.push(event)
    }
  }
}

export type AskRequest = Readonly<{
  question: string
  index_version: string
  retrieval_limit?: number
  mode: 'fixture'
}>

export async function* fetchAnswerStream(
  request: AskRequest,
  signal: AbortSignal,
  endpoint = '/api/v1/ask',
): AsyncGenerator<AnswerStreamEvent> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) throw new AnswerStreamProtocolError(`ask failed before stream: ${response.status}`)
  if (!response.headers.get('content-type')?.startsWith('text/event-stream')) {
    throw new AnswerStreamProtocolError('ask response is not an event stream')
  }
  if (response.body === null) throw new AnswerStreamProtocolError('ask response has no body')

  const parser = new AnswerStreamParser()
  const reader = response.body.getReader()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      for (const event of parser.push(value)) yield event
    }
    for (const event of parser.finish()) yield event
  } finally {
    reader.releaseLock()
  }
}
