import { getResponseErrorMessage } from './errorMessage'
import { ApiError } from './errors'

interface IdeasResponse {
  content: string
  updated_at?: string | null
}

interface IdeasSaveOptions {
  expectedUpdatedAt?: string | null
  force?: boolean
}

export class IdeasSaveConflictError extends Error {
  readonly content: string
  readonly updatedAt: string | null

  constructor(content: string, updatedAt: string | null) {
    super('Ideas file changed on disk.')
    this.name = 'IdeasSaveConflictError'
    this.content = content
    this.updatedAt = updatedAt
  }
}

export async function fetchIdeas(): Promise<IdeasResponse> {
  const response = await fetch('/api/ideas', {
    method: 'GET',
  })

  if (!response.ok) {
    const errorMessage = await getResponseErrorMessage(
      response,
      `Fetch ideas request failed with status ${response.status}`,
    )
    throw new ApiError(response.status, errorMessage)
  }

  return (await response.json()) as IdeasResponse
}

export async function saveIdeas(content: string, options: IdeasSaveOptions = {}): Promise<string | null> {
  const body: { content: string; expected_updated_at?: string | null; force?: boolean } = { content }
  if ('expectedUpdatedAt' in options) {
    body.expected_updated_at = options.expectedUpdatedAt ?? null
  }
  if (options.force === true) {
    body.force = true
  }

  const response = await fetch('/api/ideas', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    if (response.status === 409) {
      try {
        const payload = (await response.json()) as { content?: unknown; updated_at?: unknown }
        if (typeof payload.content === 'string') {
          throw new IdeasSaveConflictError(
            payload.content,
            typeof payload.updated_at === 'string' ? payload.updated_at : null,
          )
        }
      } catch (error) {
        if (error instanceof IdeasSaveConflictError) {
          throw error
        }
      }
    }

    const errorMessage = await getResponseErrorMessage(
      response,
      `Save ideas request failed with status ${response.status}`,
    )
    throw new ApiError(response.status, errorMessage)
  }

  return typeof response.headers?.get === 'function'
    ? response.headers.get('x-ideas-updated-at')
    : null
}
