import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { createDeliveryGraphFixture } from '../../e2e/support/delivery-graph-fixture'

describe('shared graph scale fixture', () => {
  it.each([14, 300])('is accepted by the canonical DeliveryGraph schema at %i nodes', (count) => {
    const workspaceRoot = resolve(process.cwd(), '../../..')
    const python = resolve(workspaceRoot, '.venv/bin/python')
    const script = [
      'import json,sys',
      'from owlbear_kanban.change import DeliveryGraph',
      'graph=DeliveryGraph.model_validate(json.load(sys.stdin))',
      'print(len(graph.nodes))',
    ].join(';')
    const fixture = createDeliveryGraphFixture(count)

    const output = execFileSync(python, ['-c', script], {
      cwd: workspaceRoot,
      input: JSON.stringify(fixture.graph),
      encoding: 'utf8',
    })

    expect(output.trim()).toBe(String(count))
  })
})
