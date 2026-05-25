import { ApiError } from './errors'
import { getResponseErrorMessage } from './errorMessage'

export interface ResolveRequest {
  selected_option_id: string | null
  free_text: string | null
  kind: 'decision' | 'action' | null
}

export interface ResolveResponse {
  request_id: string
  task_id: number
  kind: 'decision' | 'action'
  title: string
  resolved_at: string
}

export async function resolveDR(id: string, request: ResolveRequest): Promise<ResolveResponse> {
  const response = await fetch(`/api/requests/${id}/resolve`, {
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
