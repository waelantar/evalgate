import type { SearchEvidence } from '../inspection/state'

type SearchResponse = Readonly<{
  results: SearchEvidence[]
}>

export async function fetchSearchEvidence(
  question: string,
  indexVersion: string,
  signal: AbortSignal,
  limit = 10,
): Promise<SearchEvidence[]> {
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: question, index_version: indexVersion, limit }),
    signal,
  })
  if (!response.ok) throw new Error('evidence request failed')
  const payload = (await response.json()) as SearchResponse
  if (!Array.isArray(payload.results)) throw new Error('evidence response was invalid')
  return payload.results
}
