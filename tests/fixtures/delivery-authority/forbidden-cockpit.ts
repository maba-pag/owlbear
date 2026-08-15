export async function mergePullRequest(changeId: string): Promise<void> {
  await fetch(`/api/changes/${changeId}/merge`, { method: 'POST' })
}