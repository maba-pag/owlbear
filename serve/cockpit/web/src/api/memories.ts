import { getResponseErrorMessage } from './errorMessage'
import { ApiError } from './errors'

export type MemoryState = 'pending' | 'curated' | 'approved' | 'contested' | 'disputed' | 'stale' | 'deleted'

export interface MemoryEntry {
  id: string
  title: string
  content: string
  categories: string[]
  confidence: number
  state: MemoryState
  outstanding_count: number
  score: number
  scope_agents: string[]
  source_agent: string
  created_at: string
  updated_at: string
  approved_at: string | null
  contested_by_task: string | null
}

export interface MemoryEditPayload {
  title: string
  categories: string[]
  confidence: number
  scope_agents: string[]
  content: string
  expected_updated_at: string
}

export interface MemoriesResponse {
  entries: MemoryEntry[]
  parse_errors: number
}

export interface ValidationMessage {
  field: string
  message: string
}

export interface MemoryMutationResponse {
  entry?: MemoryEntry
}

export class MemoryMutationError extends Error {
  readonly apiError: ApiError
  readonly validationMessages: ValidationMessage[]

  constructor(apiError: ApiError, validationMessages: ValidationMessage[] = []) {
    super(apiError.message)
    this.name = 'MemoryMutationError'
    this.apiError = apiError
    this.validationMessages = validationMessages
  }
}

function parseValidationField(loc: unknown): string {
  if (!Array.isArray(loc)) {
    return 'form'
  }

  const field = [...loc]
    .reverse()
    .find((part) => typeof part === 'string' && part !== 'body')
  return typeof field === 'string' && field.trim().length > 0 ? field.trim() : 'form'
}

function parseValidationErrors(payload: unknown): ValidationMessage[] {
  if (typeof payload !== 'object' || payload === null) {
    return []
  }
  const detail = (payload as { detail?: unknown }).detail
  if (!Array.isArray(detail)) {
    return []
  }
  return detail
    .map((item) => {
      if (typeof item !== 'object' || item === null) {
        return null
      }
      const message = (item as { msg?: unknown }).msg
      if (typeof message !== 'string' || message.trim().length === 0) {
        return null
      }
      return {
        field: parseValidationField((item as { loc?: unknown }).loc),
        message: message.trim(),
      }
    })
    .filter((message): message is ValidationMessage => message !== null)
}

function parseMutationErrorPayload(payload: unknown): { validationMessages: ValidationMessage[]; message: string | null } {
  const validationMessages = parseValidationErrors(payload)
  if (validationMessages.length > 0) {
    return { validationMessages, message: null }
  }

  if (typeof payload === 'object' && payload !== null) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return { validationMessages: [], message: detail.trim() }
    }

    const message = (payload as { message?: unknown }).message
    if (typeof message === 'string' && message.trim().length > 0) {
      return { validationMessages: [], message: message.trim() }
    }
  }

  return { validationMessages: [], message: null }
}

async function postMemoryMutation<T>(url: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body ?? {}),
  })

  if (!response.ok) {
    let payload: unknown
    try {
      payload = (await response.json()) as unknown
    } catch {
      payload = null
    }

    const parsed = parseMutationErrorPayload(payload)
    const message =
      parsed.message ??
      (await getResponseErrorMessage(response, `Memory mutation failed with status ${response.status}`))
    throw new MemoryMutationError(new ApiError(response.status, message), parsed.validationMessages)
  }

  return (await response.json()) as T
}

export async function approveMemory(entryId: string, expectedUpdatedAt: string): Promise<MemoryMutationResponse> {
  return postMemoryMutation<MemoryMutationResponse>(`/api/memories/${entryId}/approve`, {
    expected_updated_at: expectedUpdatedAt,
  })
}

export async function resolveMemory(entryId: string, expectedUpdatedAt: string): Promise<MemoryMutationResponse> {
  return postMemoryMutation<MemoryMutationResponse>(`/api/memories/${entryId}/resolve`, {
    expected_updated_at: expectedUpdatedAt,
  })
}

export async function deleteMemory(entryId: string, expectedUpdatedAt: string): Promise<MemoryMutationResponse> {
  return postMemoryMutation<MemoryMutationResponse>(`/api/memories/${entryId}/delete`, {
    expected_updated_at: expectedUpdatedAt,
  })
}

export async function editMemory(entryId: string, payload: MemoryEditPayload): Promise<MemoryMutationResponse> {
  return postMemoryMutation<MemoryMutationResponse>(`/api/memories/${entryId}/edit`, payload as unknown as Record<string, unknown>)
}
