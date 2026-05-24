import { getResponseErrorMessage } from './errorMessage'
import { ApiError } from './errors'

interface IdeasResponse {
  content: string
  updated_at?: string | null
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

export async function saveIdeas(content: string): Promise<string | null> {
  const response = await fetch('/api/ideas', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
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
