export async function publishMerge(changeId: string): Promise<void> {
  await fetch(`/api/changes/${changeId}/merge`, { method: 'POST' })
}

const autoMergeEnabled = 'auto-merge'