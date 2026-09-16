export type ClientProblem = Readonly<{
  code: string
  title: string
  detail: string
  requestId: string | null
}>

export class ProblemResponseError extends Error {
  readonly problem: ClientProblem

  constructor(problem: ClientProblem) {
    super(problem.title)
    this.name = 'ProblemResponseError'
    this.problem = problem
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export async function problemFromResponse(response: Response): Promise<ProblemResponseError | null> {
  try {
    const payload: unknown = await response.json()
    if (
      !isRecord(payload) ||
      typeof payload.code !== 'string' ||
      typeof payload.title !== 'string' ||
      typeof payload.detail !== 'string'
    ) return null
    return new ProblemResponseError({
      code: payload.code,
      title: payload.title,
      detail: payload.detail,
      requestId: typeof payload.request_id === 'string' ? payload.request_id : null,
    })
  } catch {
    return null
  }
}
