import { ApiError } from './errors'
import { getResponseErrorMessage } from './errorMessage'

export interface ResolveRequest {
  response: 'approved' | 'needs-info' | 'rejected'
  notes?: string
}

export interface ResolveResponse {
  id: string
  response: 'approved' | 'needs-info' | 'rejected'
}

export async function resolveDR(id: string, request: ResolveRequest): Promise<ResolveResponse> {
  const response = await fetch(`/api/decisions/${id}/resolve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorMessage = await getResponseErrorMessage(
      response,
      `Resolve request failed with status ${response.status}`,
    )
    throw new ApiError(response.status, errorMessage)
  }

  return (await response.json()) as ResolveResponse
}
