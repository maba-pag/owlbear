import { getResponseErrorMessage } from './errorMessage'
import { ApiError } from './errors'

export interface TaskDetail {
  id: number
  title: string
  status: string
  priority: string
  updated: string
  created: string
  body: string | null
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
  claimed_at: string | null
  dep_status: string | null
  parent: number | null
  depends_on: number[]
}

export interface MoveRequest {
  status: string
  updated: string
  archival_reason?: string | null
  archival_refs?: number[] | null
}

export interface EditRequest {
  updated: string
  title?: string | null
  tags?: string[] | null
  priority?: string | null
  depends_on?: number[] | null
  parent?: number | null
  block_reason?: string | null
  body?: string | null
}

export interface ReleaseRequest {
  updated: string
}

interface GetTaskOptions {
  signal?: AbortSignal
}

async function parseTaskResponse(response: Response, fallbackMessage: string): Promise<TaskDetail> {
  if (!response.ok) {
    const errorMessage = await getResponseErrorMessage(response, fallbackMessage)
    throw new ApiError(response.status, errorMessage)
  }

  return (await response.json()) as TaskDetail
}

export async function getTask(id: number, options?: GetTaskOptions): Promise<TaskDetail> {
  const response = await fetch(`/api/tasks/${id}`, {
    method: 'GET',
    signal: options?.signal,
  })

  return parseTaskResponse(response, `Get task request failed with status ${response.status}`)
}

export async function moveTask(id: number, request: MoveRequest): Promise<TaskDetail> {
  const response = await fetch(`/api/tasks/${id}/move`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  return parseTaskResponse(response, `Move task request failed with status ${response.status}`)
}

export async function editTask(id: number, request: EditRequest): Promise<TaskDetail> {
  const response = await fetch(`/api/tasks/${id}/edit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  return parseTaskResponse(response, `Edit task request failed with status ${response.status}`)
}

export async function releaseTask(id: number, request: ReleaseRequest): Promise<TaskDetail> {
  const response = await fetch(`/api/tasks/${id}/release`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  return parseTaskResponse(response, `Release task request failed with status ${response.status}`)
}
