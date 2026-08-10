import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises'
import { once } from 'node:events'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { spawn } from 'node:child_process'

const root = resolve(import.meta.dirname, '../../../../..')
const fixture = await mkdtemp(join(tmpdir(), 'owlbear-memory-lifecycle-'))
const memoryDir = join(fixture, '.owlbear/memory')
const fixtureManifest = resolve(import.meta.dirname, '../../test-results/memory-lifecycle-fixture.json')
const mcpProof = resolve(import.meta.dirname, '../../test-results/memory-lifecycle-mcp.json')
await mkdir(memoryDir, { recursive: true })

const entries = [
  ['11111111-1111-4111-8111-111111111111', 'Approved memory', 'approved', 0.95, null],
  ['66666666-6666-4666-8666-666666666666', 'Pending memory', 'pending', 0.88, null],
  ['77777777-7777-4777-8777-777777777777', 'Curated memory', 'curated', 0.84, null],
  ['22222222-2222-4222-8222-222222222222', 'Contested memory', 'contested', 0.82, '1960'],
  ['33333333-3333-4333-8333-333333333333', 'Disputed memory', 'disputed', 0.71, '1956'],
  ['44444444-4444-4444-8444-444444444444', 'Stale memory', 'stale', 0.61, null],
  ['55555555-5555-4555-8555-555555555555', 'Deleted memory', 'deleted', 0.2, null],
]
for (const [id, title, state, score, contestedByTask] of entries) {
  const frontmatter = [
    '---', `id: ${id}`, `title: ${title}`, 'categories: [process]', 'confidence: 0.9', `state: ${state}`,
    'outstanding_count: 2', 'unremarkable_count: 0', 'didnt_use_count: 0', `score: ${score}`,
    'scope_agents: [builder]', 'source_agent: builder', 'created_at: "2025-01-01T00:00:00Z"',
    'updated_at: "2025-01-01T00:00:00Z"', 'approved_at: null',
    `contested_by_task: ${contestedByTask === null ? 'null' : `"${contestedByTask}"`}`, '---', '',
    `Lifecycle fixture content for ${title}.`, '',
  ]
  await writeFile(join(memoryDir, `${id}.md`), frontmatter.join('\n'))
}
await mkdir(resolve(fixtureManifest, '..'), { recursive: true })
await writeFile(fixtureManifest, JSON.stringify({ memoryDir }))
await rm(mcpProof, { force: true })

// The cockpit backend refuses to boot without a Delivery config, even for Memory-only runs.
const deliverySeed = spawn('uv', [
  'run',
  '--project',
  root,
  'python',
  resolve(import.meta.dirname, 'seed-work-portfolio-delivery.py'),
  '--workspace',
  fixture,
], { cwd: root, stdio: 'inherit' })
const [deliverySeedExit] = await once(deliverySeed, 'exit')
if (deliverySeedExit !== 0) {
  await rm(fixtureManifest, { force: true })
  await rm(fixture, { recursive: true, force: true })
  process.exit(deliverySeedExit ?? 1)
}

const mcpProbe = spawn('uv', [
  'run',
  '--project',
  root,
  'python',
  resolve(import.meta.dirname, 'prove-memory-lifecycle-mcp.py'),
  '--root',
  root,
  '--memory-dir',
  memoryDir,
  '--output',
  mcpProof,
], { cwd: root, stdio: 'inherit' })
const [mcpProbeExit] = await once(mcpProbe, 'exit')
if (mcpProbeExit !== 0) {
  await rm(fixtureManifest, { force: true })
  await rm(fixture, { recursive: true, force: true })
  process.exit(mcpProbeExit ?? 1)
}

const server = spawn('uv', ['run', '--project', root, '--package', 'owlbear-cockpit', 'cockpit'], {
  cwd: fixture,
  env: {
    ...process.env,
    COCKPIT_PORT: '8422',
    COCKPIT_NO_OPEN: '1',
  },
  stdio: 'inherit',
})
const cleanup = async () => {
  if (!server.killed) server.kill('SIGTERM')
  await rm(fixtureManifest, { force: true })
  await rm(fixture, { recursive: true, force: true })
}
process.on('SIGTERM', cleanup)
process.on('SIGINT', cleanup)
server.on('exit', async (code) => { await cleanup(); process.exit(code ?? 1) })
