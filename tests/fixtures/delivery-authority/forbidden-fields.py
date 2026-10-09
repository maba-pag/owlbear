def forbidden_response():
    return {
        "merge_method": "squash",
        "mergeMethod": "squash",
    }


class BaseModel: ...


class CompletionEvidence(BaseModel):
    merge_method: str


class MergedPullRequestLatch(BaseModel):
    merge_method: str


class AcceptanceObservation(BaseModel):
    mergeMethod: str  # noqa: N815


class PublicationPullRequest(BaseModel):
    merge_method: str
