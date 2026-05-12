function readMessageField(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null) {
    return null
  }

  const record = payload as Record<string, unknown>
  const message = typeof record.message === 'string' ? record.message.trim() : ''
  if (message.length > 0) {
    return message
  }

  const detail = typeof record.detail === 'string' ? record.detail.trim() : ''
  if (detail.length > 0) {
    return detail
  }

  return null
}

export async function getResponseErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = (await response.json()) as unknown
    const fromBody = readMessageField(payload)
    if (fromBody !== null) {
      return fromBody
    }
  } catch {
    // Ignore JSON parse failures and continue with fallback.
  }

  return fallbackMessage
}
