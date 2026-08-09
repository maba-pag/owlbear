import { mkdtemp, rm } from 'node:fs/promises'
import { once } from 'node:events'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { spawn } from 'node:child_process'

const root = resolve(import.meta.dirname, '../../../../..')
const fixture = await mkdtemp(join(tmpdir(), 'owlbear-work-portfolio-'))

async function run(command, arguments_) {
  const process = spawn(command, arguments_, { cwd: root, stdio: 'inherit' })
  const [exitCode] = await once(process, 'exit')
  if (exitCode !== 0) throw new Error(`${command} exited with ${exitCode ?? 'no status'}`)
}

try {
  await run('uv', [
    'run',
    '--project', root,
    'python',
    resolve(import.meta.dirname, 'seed-target-cockpit-workspace.py'),
    '--workspace', fixture,
  ])
  await run('uv', [
    'run',
    '--project', root,
    'python',
    resolve(import.meta.dirname, 'seed-work-portfolio-delivery.py'),
    '--workspace', fixture,
  ])
} catch (error) {
  await rm(fixture, { recursive: true, force: true })
  throw error
}

const server = spawn('uv', ['run', '--project', root, '--package', 'owlbear-cockpit', 'cockpit'], {
  cwd: fixture,
  env: {
    ...process.env,
    COCKPIT_PORT: '4175',
    COCKPIT_NO_OPEN: '1',
  },
  stdio: 'inherit',
})

const cleanup = async () => {
  if (!server.killed) server.kill('SIGTERM')
  await rm(fixture, { recursive: true, force: true })
}

process.on('SIGTERM', cleanup)
process.on('SIGINT', cleanup)
server.on('exit', async (code) => {
  await cleanup()
  process.exit(code ?? 1)
})
