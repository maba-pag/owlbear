_ENQUEUE_MUTATION = """mutation Enqueue($pullRequestId: ID!) {
  enqueuePullRequest(input: {pullRequestId: $pullRequestId}) { clientMutationId }
}"""


def merge_request_body(request):
    return {
        "bypass_rules": True,
        "merge_action": "merge_queue",
        "merge_method": request.merge_method.value,
        "sha": request.expected_head_sha,
    }


def _merge_async_endpoint(repository, number):
    return f"repos/{repository}/pulls/{number}/merge"


class ForbiddenMergeProvider:
    def merge_anywhere(self, request, body_path, release):
        endpoint = _merge_async_endpoint(request.repository, request.number)
        return self._rest_effect("merge_anywhere", "PUT", endpoint, body_path=body_path, release=release)

    def request_merge(self, request):
        return self._rest("request_merge", "PUT", f"repos/{request.repository}/pulls/{request.number}/merge-async")

    def update_branch(self, repository, number):
        return self._rest("update_branch", "PUT", f"repos/{repository}/pulls/{number}/update-branch", write=True)

    def enqueue(self, node_id):
        return self._graphql("enqueue", {"query": _ENQUEUE_MUTATION, "variables": {"pullRequestId": node_id}})
