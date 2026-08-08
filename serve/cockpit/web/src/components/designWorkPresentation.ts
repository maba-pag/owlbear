const MINOR_WORDS = new Set(['a', 'an', 'and', 'for', 'of', 'or', 'the', 'to'])

export function designWorkTitle(changeId: string): string {
  return changeId
    .split('-')
    .map((word, index) => index > 0 && MINOR_WORDS.has(word) ? word : `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ')
}

export function designCommand(changeId: string): string {
  return `/design ${changeId}`
}
