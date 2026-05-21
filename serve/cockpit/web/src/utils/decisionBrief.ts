export type DecisionBriefSource = {
  title: string
  task_id: number
  body: string
  body_preview: string
}

export type DecisionBrief = {
  title: string
  context: string
  options: string[]
  recommendation: string | null
  consequence: string | null
  request: string
}

function truncatePreview(value: string): string {
  return value.slice(0, 200)
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function stripMarkdown(value: string): string {
  return normalizeWhitespace(
    value
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^[-*+]\s+/gm, '')
      .replace(/^\d+\.\s+/gm, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_`>]/g, ''),
  )
}

function removeLeadingTitle(body: string, title: string): string {
  const titleText = normalizeWhitespace(stripMarkdown(title))
  if (!titleText) {
    return body.trim()
  }

  const lines = body.trim().split('\n')
  const firstContentIndex = lines.findIndex((line) => line.trim().length > 0)
  if (firstContentIndex === -1) {
    return ''
  }

  const firstContent = lines[firstContentIndex].trim().replace(/^#{1,6}\s+/, '')
  if (normalizeWhitespace(stripMarkdown(firstContent)) !== titleText) {
    return body.trim()
  }

  const remaining = lines.slice(0, firstContentIndex).concat(lines.slice(firstContentIndex + 1))
  while (remaining[0]?.trim() === '') {
    remaining.shift()
  }
  return remaining.join('\n').trim()
}

function removeTitleOnlyPreview(value: string, title: string): string {
  const text = stripMarkdown(value)
  const titleText = stripMarkdown(title)
  return text === titleText ? '' : text
}

function extractRawSection(body: string, sectionNames: string[]): string | null {
  const lines = body.split('\n')
  const sectionMatcher = new RegExp(`^#{1,6}\\s+(${sectionNames.map(escapeRegExp).join('|')})\\s*$`, 'i')
  let startIndex = -1

  for (const [index, line] of lines.entries()) {
    if (sectionMatcher.test(line.trim())) {
      startIndex = index + 1
      break
    }
  }

  if (startIndex === -1) {
    return null
  }

  const sectionLines: string[] = []
  for (let index = startIndex; index < lines.length; index += 1) {
    if (/^#{1,6}\s+/.test(lines[index].trim())) {
      break
    }
    sectionLines.push(lines[index])
  }

  const rawText = sectionLines.join('\n').trim()
  return rawText.length > 0 ? rawText : null
}

function extractSection(body: string, sectionNames: string[]): string | null {
  const rawText = extractRawSection(body, sectionNames)
  if (!rawText) {
    return null
  }
  const text = stripMarkdown(rawText)
  return text.length > 0 ? text : null
}

function extractOptions(body: string): string[] {
  const optionSection = extractRawSection(body, ['Options', 'Choices', 'Alternatives'])
  if (!optionSection) {
    return []
  }

  const optionLines = optionSection
    .split('\n')
    .map((line) => line.match(/^\s*(?:[-*+]|\d+\.)\s+(.+)$/)?.[1] ?? '')
    .map((option) => stripMarkdown(option))
    .filter(Boolean)
  if (optionLines.length > 0) {
    return optionLines.slice(0, 4)
  }
  return [truncatePreview(stripMarkdown(optionSection))]
}

export function formatAge(created: string): string {
  const parsedCreated = Date.parse(created)
  const createdAt = Number.isFinite(parsedCreated) ? parsedCreated : Date.now()
  const ageMs = Math.max(0, Date.now() - createdAt)
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))
  const unitIndex = Number(ageMinutes >= 60) + Number(ageMinutes >= 24 * 60)
  const divisors = [1, 60, 24 * 60]
  const units = ['m', 'h', 'd']
  const value = Math.floor(ageMinutes / divisors[unitIndex])
  return `${value}${units[unitIndex]} ago`
}

export function formatRequestType(value: string): string {
  return value
    .replace(/[-_]/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function formatDecisionTitle(item: { title: string; task_id: number }): string {
  const title = item.title.trim()
  return title || `Decision needed for task #${item.task_id}`
}

export function getDecisionBodyMarkdown(item: DecisionBriefSource): string {
  return removeLeadingTitle(item.body ?? '', item.title)
}

export function getDecisionBrief(item: DecisionBriefSource): DecisionBrief {
  const title = formatDecisionTitle(item)
  const body = getDecisionBodyMarkdown(item)
  const preview = removeTitleOnlyPreview(item.body_preview || '', title)
  const fallbackText = preview || stripMarkdown(body || item.body)
  const context = extractSection(body, ['Context', 'Question', 'Decision', 'Request'])
    ?? fallbackText
  const recommendation = extractSection(body, ['Recommendation', 'Recommended response', 'Proposal'])
  const consequence = extractSection(body, ['Consequence', 'Consequences', 'Impact'])
  return {
    title,
    context: truncatePreview(context),
    options: extractOptions(body),
    recommendation: recommendation ? truncatePreview(recommendation) : null,
    consequence: consequence ? truncatePreview(consequence) : null,
    request: truncatePreview(fallbackText),
  }
}
