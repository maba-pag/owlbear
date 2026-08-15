class ForbiddenProvider:
    _MERGE_MUTATION = """mutation MergePullRequest($pullRequestId: ID!) {
      enablePullRequestAutoMerge(input: {pullRequestId: $pullRequestId}) { clientMutationId }
    }"""

    def merge_pull_request(self, repository: str, number: int):
        return self._rest("merge_pull_request", "POST", f"repos/{repository}/pulls/{number}/merge", write=True)

    def enable_auto_merge(self, node_id: str):
        return self._graphql("enable_auto_merge", {"query": self._MERGE_MUTATION, "variables": {"id": node_id}})