function readValidationField(loc: unknown): string | null {
  if (!Array.isArray(loc)) {
    return null
  }

  const parts = loc
    .filter((item): item is string => typeof item === 'string')
    .filter((item) => !['body', 'query', 'path'].includes(item))

  return parts.length > 0 ? parts[parts.length - 1] : null
}

function readDetailArray(detail: unknown): string | null {
  if (!Array.isArray(detail)) {
    return null
  }

  const messages = detail
    .map((item) => {
      if (typeof item === 'string') {
        return item.trim()
      }

      if (typeof item !== 'object' || item === null) {
        return ''
      }

      const record = item as Record<string, unknown>
      const message = typeof record.msg === 'string' ? record.msg.trim() : ''
      if (message.length === 0) {
        return ''
      }

      const field = readValidationField(record.loc)
      return field !== null ? `${field}: ${message}` : message
    })
    .filter((message) => message.length > 0)

  return messages.length > 0 ? messages.join('; ') : null
}

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

  const detailArray = readDetailArray(record.detail)
  if (detailArray !== null) {
    return detailArray
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
