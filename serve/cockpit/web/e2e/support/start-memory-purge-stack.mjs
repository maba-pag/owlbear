import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { execFile, spawn } from 'node:child_process'
import { promisify } from 'node:util'

const runFile = promisify(execFile)

const root = resolve(import.meta.dirname, '../../../../..')
const fixture = await mkdtemp(join(tmpdir(), 'owlbear-memory-purge-'))
const memoryDir = join(fixture, '.owlbear/memory')
const fixtureManifest = resolve(import.meta.dirname, '../../test-results/memory-purge-fixture.json')
await mkdir(memoryDir, { recursive: true })

const now = Date.now()
const daysAgo = (days) => new Date(now - days * 24 * 60 * 60 * 1000).toISOString()
const entries = [
  ['11111111-1111-4111-8111-111111111111', 'Eligible deleted', 'deleted', daysAgo(30)],
  ['22222222-2222-4222-8222-222222222222', 'Exact cutoff deleted', 'deleted', daysAgo(1)],
  ['33333333-3333-4333-8333-333333333333', 'Recent deleted', 'deleted', daysAgo(0)],
  ['44444444-4444-4444-8444-444444444444', 'Active memory', 'approved', daysAgo(30)],
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
await runFile('uv', [
  'run',
  '--project',
  root,
  'python',
  resolve(import.meta.dirname, 'seed-target-cockpit-workspace.py'),
  '--workspace',
  fixture,
], { cwd: root })
// The cockpit backend refuses to boot without a Delivery config, even for Memory-only runs.
await runFile('uv', [
  'run',
  '--project',
  root,
  'python',
  resolve(import.meta.dirname, 'seed-work-portfolio-delivery.py'),
  '--workspace',
  fixture,
], { cwd: root })

const server = spawn('uv', ['run', '--project', root, '--package', 'owlbear-cockpit', 'cockpit'], {
  cwd: fixture,
  env: {
    ...process.env,
    COCKPIT_PORT: '8421',
    COCKPIT_NO_OPEN: '1',
  },
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
