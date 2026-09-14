export type InspectionCatalogItem = Readonly<{
  index_version: string
  index_key: string
  corpus_key: string
  corpus_version: string
  label: string
}>

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function item(value: unknown): InspectionCatalogItem {
  if (
    !isRecord(value) ||
    typeof value.index_version !== 'string' ||
    typeof value.index_key !== 'string' ||
    typeof value.corpus_key !== 'string' ||
    typeof value.corpus_version !== 'string' ||
    typeof value.label !== 'string'
  ) {
    throw new Error('inspection catalog returned an invalid response')
  }
  return value as InspectionCatalogItem
}

export async function fetchInspectionCatalog(signal?: AbortSignal): Promise<readonly InspectionCatalogItem[]> {
  const init: RequestInit = { headers: { Accept: 'application/json' } }
  if (signal !== undefined) init.signal = signal
  const response = await fetch('/api/v1/inspection-catalog', {
    ...init,
  })
  if (!response.ok) throw new Error('inspection catalog is unavailable')
  const payload: unknown = await response.json()
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error('inspection catalog returned an invalid response')
  }
  return payload.items.map(item)
}
