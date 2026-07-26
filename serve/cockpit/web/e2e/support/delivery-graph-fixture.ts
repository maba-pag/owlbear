import type { NativeGraphDetail } from '../../src/api/native'

function stable(prefix: string, index: number): string {
  return `${prefix}-${String(index).padStart(3, '0')}`
}

export function createDeliveryGraphFixture(count: number, changeId = 'fixture-change'): NativeGraphDetail {
  const migrations = Array.from({ length: 4 }, (_, index) => {
    const number = index + 1
    return {
      id: stable('MIG', number),
      title: `Migration ${number}`,
      owner: 'DN-001',
      from: `legacy-${number}`,
      to: `native-${number}`,
      ordered_steps: ['prepare', 'switch'],
      consumer_inventory: ['fixture consumer'],
      compatibility: 'No compatibility window',
      deletion_owner: 'DN-001',
      absence_proof: 'PROOF-001',
    }
  })
  const nodes = Array.from({ length: count }, (_, index) => {
    const number = index + 1
    const id = stable('DN', number)
    return {
      id,
      title: `Delivery node ${number}`,
      outcome: `Outcome for ${id}`,
      owns: [stable('REQ', number)],
      supports: [],
      modules: [stable('MOD', number)],
      produces: [stable('IF', number)],
      consumes: number > 1 ? [stable('IF', number - 1)] : [],
      dependencies: number > 1 ? [stable('DN', number - 1)] : [],
      risks: [stable('RISK', number)],
      proof: stable('PROOF', number),
    }
  })
  const requirements = nodes.map((item, index) => ({
    id: item.owns[0],
    title: `Requirement ${index + 1}`,
    statement: `Requirement for ${item.id}`,
    workflows: [],
  }))
  const modules = nodes.map((item) => ({
    id: item.modules[0],
    paths: [`serve/fixture/${item.id}/`],
    current_responsibility: `Current ${item.id}`,
    planned_change: `Planned ${item.id}`,
  }))
  const proofs = nodes.map((item) => ({
    id: item.proof,
    title: `Proof ${item.id}`,
    boundary: 'Fixture boundary',
    owner: item.id,
    method: ['Fixture method'],
    allowed_replacements: [],
    durable_outputs: ['fixture output'],
  }))
  const risks = nodes.map((item) => ({
    id: item.risks[0],
    class: 'integration',
    title: `Risk ${item.id}`,
    scenarios: ['Fixture scenario'],
    disposition: 'Prove with fixture',
    owner: item.id,
    supporting_nodes: [],
    proof: item.proof,
  }))
  const interfaces = nodes.map((item, index) => ({
    id: item.produces[0],
    name: `Interface ${item.id}`,
    producer: item.id,
    consumers: index + 1 < nodes.length ? [nodes[index + 1].id] : [],
    contract: `Contract for ${item.id}`,
    authority: item.modules[0],
    failure_semantics: 'Fail closed',
    migration: migrations[index % migrations.length].id,
    proof: item.proof,
  }))
  const deliveryDigest = 'a'.repeat(64)

  return {
    change_id: changeId,
    delivery_digest: deliveryDigest,
    graph: {
      schema_version: 1,
      change_id: changeId,
      state: 'admitted',
      authority: { intent: 'intent.md', design: 'design.md', decisions: 'decisions.yaml', research: [] },
      admission: { state: 'admitted', delivery_digest: deliveryDigest, receipt: 'receipt.yaml', limits: [] },
      requirements,
      negative_requirements: [],
      preserved_behaviors: [],
      workflows: [],
      modules,
      interfaces,
      migrations,
      risks,
      proofs,
      nodes,
    },
    plans: Object.fromEntries(
      nodes.map((item, index) => [
        item.id,
        {
          packets: [
            {
              id: `${item.id}-PK-001`,
              dependencies: index > 0 ? [`${nodes[index - 1].id}-PK-001`] : [],
              impact_closure: { paths: ['serve/'], authority_targets: [item.id, item.proof] },
            },
          ],
        },
      ]),
    ),
  }
}
