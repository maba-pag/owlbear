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

    const nodeIds = new Set(fixture.graph.nodes.map((node) => node.id))
    const entityIds = new Set([
      ...fixture.graph.nodes.map((node) => node.id),
      ...fixture.graph.proofs.map((proof) => String(proof.id)),
    ])
    for (const [nodeId, plan] of Object.entries(fixture.plans)) {
      expect(nodeIds.has(nodeId)).toBe(true)
      const packetIds = new Set(plan.packets.map((packet) => packet.id))
      for (const packet of plan.packets) {
        expect(packet.dependencies.every((dependency) => packetIds.has(dependency))).toBe(true)
        expect(packet.impact_closure.authority_targets.every((target) => entityIds.has(target))).toBe(true)
      }
    }
  })
})
