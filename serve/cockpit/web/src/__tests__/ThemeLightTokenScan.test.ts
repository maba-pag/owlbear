import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SRC_DIR = resolve(__dirname, '..')
const LEGACY_TOKEN_PATTERN = /--pds-theme-light-[a-z0-9-]+/g

function findSourceFiles(dir: string): string[] {
  const excludedDirs = new Set(['__tests__', 'node_modules', 'dist', 'build'])
  const acceptedExtensions = new Set(['.css', '.ts', '.tsx'])
  const files: string[] = []

  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = resolve(dir, entry.name)
    if (entry.isDirectory()) {
      if (!excludedDirs.has(entry.name)) {
        files.push(...findSourceFiles(fullPath))
      }
      continue
    }

    if (!entry.isFile()) {
      continue
    }

    const dotIndex = entry.name.lastIndexOf('.')
    const ext = dotIndex >= 0 ? entry.name.slice(dotIndex) : ''
    if (acceptedExtensions.has(ext)) {
      files.push(fullPath)
    }
  }

  return files
}

function findLegacyTokenViolations(filePath: string): string[] {
  const source = readFileSync(filePath, 'utf-8')
  const relativePath = filePath.replace(`${SRC_DIR}/`, 'src/')
  const violations: string[] = []

  for (const [lineIndex, line] of source.split('\n').entries()) {
    const matches = [...line.matchAll(LEGACY_TOKEN_PATTERN)]
    for (const match of matches) {
      violations.push(`${relativePath}:${lineIndex + 1}: ${match[0]}`)
    }
  }

  return violations
}

describe('TestFromAC_ThemeLightTokenScan_1552', () => {
  it('AC-1/AC-3: src production files contain no --pds-theme-light-* tokens', () => {
    const files = findSourceFiles(SRC_DIR)
    expect(files.length, 'source tree should contain files to scan').toBeGreaterThan(0)

    const violations: string[] = []
    for (const filePath of files) {
      violations.push(...findLegacyTokenViolations(filePath))
    }

    expect(
      violations,
      `Found legacy --pds-theme-light-* token usage in production files:\n${violations.join('\n')}`,
    ).toEqual([])
  })
})
