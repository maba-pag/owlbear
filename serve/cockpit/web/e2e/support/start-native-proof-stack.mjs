import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { once } from 'node:events'
import { spawn } from 'node:child_process'

const root = resolve(import.meta.dirname, '../../../../..')
const workspace = await mkdtemp(join(tmpdir(), 'owlbear-native-proof-'))
const seed = spawn('uv', [
  'run', '--project', root, 'python', resolve(import.meta.dirname, 'seed-native-proof-stack.py'),
  '--project-root', root, '--workspace', workspace,
], { cwd: root, stdio: 'inherit' })
const [seedExit] = await once(seed, 'exit')
if (seedExit !== 0) {
  await rm(workspace, { recursive: true, force: true })
  process.exit(seedExit ?? 1)
}

const server = spawn('uv', ['run', '--project', root, '--package', 'owlbear-cockpit', 'cockpit'], {
  cwd: workspace,
  env: {
    ...process.env,
    OWLBEAR_WORK_ROOT: join(workspace, '.owlbear', 'kanban'),
    MEMORY_DIR: join(workspace, '.owlbear', 'memory'),
    COCKPIT_PORT: '8423',
    COCKPIT_NO_OPEN: '1',
  },
  stdio: 'inherit',
})
let cleaning = false
const cleanup = async () => {
  if (cleaning) return
  cleaning = true
  if (!server.killed) server.kill('SIGTERM')
  await rm(workspace, { recursive: true, force: true })
}
process.on('SIGTERM', cleanup)
process.on('SIGINT', cleanup)
server.on('exit', async (code) => {
  await cleanup()
  process.exit(code ?? 1)
})
