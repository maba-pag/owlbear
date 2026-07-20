import { cp, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { execFile, spawn } from 'node:child_process'
import { promisify } from 'node:util'

const runFile = promisify(execFile)

const root = resolve(import.meta.dirname, '../../../../..')
const fixture = await mkdtemp(join(tmpdir(), 'owlbear-memory-purge-'))
const kanbanDir = join(fixture, 'kanban')
const memoryDir = join(fixture, 'memory')
const fixtureManifest = resolve(import.meta.dirname, '../../test-results/memory-purge-fixture.json')
await mkdir(memoryDir)
await cp(join(root, '.owlbear', 'kanban'), kanbanDir, { recursive: true })

const entries = [
  ['11111111-1111-4111-8111-111111111111', 'Eligible deleted', 'deleted', '2025-01-01T00:00:00Z'],
  ['22222222-2222-4222-8222-222222222222', 'Exact cutoff deleted', 'deleted', '2026-07-19T00:00:00Z'],
  ['33333333-3333-4333-8333-333333333333', 'Recent deleted', 'deleted', '2026-07-20T00:00:00Z'],
  ['44444444-4444-4444-8444-444444444444', 'Active memory', 'approved', '2025-01-01T00:00:00Z'],
]
for (const [id, title, state, updatedAt] of entries) {
  const frontmatter = [
    '---',
    `id: ${id}`,
    `title: ${title}`,
    'categories: [process]',
    'confidence: 0.9',
    `state: ${state}`,
    'outstanding_count: 0',
    'unremarkable_count: 0',
    'didnt_use_count: 0',
    'score: 0.9',
    'scope_agents: [builder]',
    'source_agent: builder',
    `created_at: "${updatedAt}"`,
    `updated_at: "${updatedAt}"`,
    'approved_at: null',
    'contested_by_task: null',
    '---',
    '',
    'Fixture content',
    '',
  ]
  await writeFile(join(memoryDir, `${id}.md`), frontmatter.join('\n'))
}
await mkdir(resolve(fixtureManifest, '..'), { recursive: true })
await writeFile(fixtureManifest, JSON.stringify({ memoryDir }))

const server = spawn('uv', ['run', '--project', root, '--package', 'owlbear-cockpit', 'cockpit'], {
  cwd: root,
  env: { ...process.env, KANBAN_DIR: kanbanDir, MEMORY_DIR: memoryDir, COCKPIT_PORT: '8421', COCKPIT_NO_OPEN: '1' },
  stdio: 'inherit',
})
const cleanup = async () => {
  if (!server.killed) server.kill('SIGTERM')
  await rm(fixtureManifest, { force: true })
  await Promise.all(
    entries.map(([id]) => runFile('chflags', ['nouchg', join(memoryDir, `${id}.md`)]).catch(() => undefined)),
  )
  await rm(fixture, { recursive: true, force: true })
}
process.on('SIGTERM', cleanup)
process.on('SIGINT', cleanup)
server.on('exit', async (code) => {
  await cleanup()
  process.exit(code ?? 1)
})
