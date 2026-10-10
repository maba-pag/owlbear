# Adapted from serve/delivery-github/src/owlbear_delivery_github/github.py at ab9cfc6cb.
"""``gh`` conversation: read every comment, review and thread; reply and resolve as the viewer."""

from __future__ import annotations

from pydantic import ValidationError

from owlbear_delivery_next.github.gh_client import GhClient, Json, invalid, repo
from owlbear_delivery_next.github.provider import ConversationItem, FailureCode, ProviderError, ThreadComment

_CONVERSATION = """query Conversation($owner: String!, $name: String!, $number: Int!,
    $c: String, $r: String, $t: String, $wc: Boolean!, $wr: Boolean!, $wt: Boolean!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) {
    comments(first: 100, after: $c) @include(if: $wc) { pageInfo { hasNextPage endCursor }
      nodes { id url body author { login } } }
    reviews(first: 100, after: $r) @include(if: $wr) { pageInfo { hasNextPage endCursor }
      nodes { id url body state author { login } } }
    reviewThreads(first: 100, after: $t) @include(if: $wt) { pageInfo { hasNextPage endCursor }
      nodes { id path isResolved isOutdated
        comments(first: 100) { pageInfo { hasNextPage endCursor } nodes { id url body author { login } } } } } } }
}"""
_THREAD_COMMENTS = """query ThreadComments($id: ID!, $after: String) {
  node(id: $id) { ... on PullRequestReviewThread {
    comments(first: 100, after: $after) { pageInfo { hasNextPage endCursor }
      nodes { id url body author { login } } } } }
}"""
_REPLY = """mutation Reply($id: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $id, body: $body}) { comment { id } }
}"""
_RESOLVE = """mutation Resolve($id: ID!) {
  resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } }
}"""
_CONNECTIONS = (("comments", "c", "wc"), ("reviews", "r", "wr"), ("reviewThreads", "t", "wt"))


def _login(node: Json) -> str:
    return (node.get("author") or {}).get("login") or "ghost"


def _thread(node: Json, nodes: list[Json], operation: str) -> ConversationItem:
    comments = tuple(ThreadComment(id=c["id"], author=_login(c), body=c["body"]) for c in nodes)
    if not comments:
        invalid(operation, "a review thread has no comments")
    first = nodes[0]
    return ConversationItem(
        id=node["id"],
        kind="thread",
        author=comments[0].author,
        body="\n".join(f"{c.author}: {c.body}" for c in comments),
        url=first["url"],
        path=node.get("path"),
        resolved=node["isResolved"],
        outdated=node["isOutdated"],
        comments=comments,
    )


def _items(name: str, nodes: Json) -> list[ConversationItem]:
    kind = "comment" if name == "comments" else "review"
    return [
        ConversationItem(
            id=n["id"],
            kind=kind,
            author=_login(n),
            body=n["body"] or "",
            url=n["url"],
            state=n.get("state") or "",
        )
        for n in nodes
        if kind == "comment" or (n["body"] or "").strip() or n["state"] == "CHANGES_REQUESTED"
    ]


class Conversation(GhClient):
    """Read a pull request's conversation and answer it as the viewer."""

    def viewer(self) -> str:
        """Read the login Delivery posts as, once per provider; a credential that cannot read it is a capability gap."""
        if not self._viewer:
            try:
                user = self._gh("viewer", ("api", "--hostname", self.host, "user"))
            except ProviderError:
                user = None
            login = user.get("login") if isinstance(user, dict) else None
            if not isinstance(login, str) or not login:
                detail = (
                    "the GitHub credential cannot read /user, which Delivery needs to recognise its own replies; "
                    "use a user token via `gh auth login`"
                )
                raise ProviderError(FailureCode.AUTHENTICATION_REQUIRED, "viewer", detail, retry_safe=False)
            self._viewer = login
        return self._viewer

    def _thread_comments(self, op: str, node: Json) -> list[Json]:
        """Every comment of one review thread, following its comment pages."""
        page = node["comments"]
        nodes = list(page["nodes"])
        while page["pageInfo"]["hasNextPage"]:
            variables = {"id": node["id"], "after": page["pageInfo"]["endCursor"]}
            page = self._graphql(op, _THREAD_COMMENTS, variables)["data"]["node"]["comments"]
            nodes += page["nodes"]
        return nodes

    def read_conversation(self, repository: str, number: int) -> tuple[ConversationItem, ...]:
        """Read issue comments, review bodies (non-empty or changes requested) and review threads, every page."""
        op, (owner, name) = "read_conversation", repository.split("/", 1)
        found: dict[str, list[ConversationItem]] = {c: [] for c, _, _ in _CONNECTIONS}
        cursors: dict[str, str | None] = {cursor: None for _, cursor, _ in _CONNECTIONS}
        wanted = {flag: True for _, _, flag in _CONNECTIONS}
        while any(wanted.values()):
            variables = {"owner": owner, "name": name, "number": number, **cursors, **wanted}
            result = self._graphql(op, _CONVERSATION, variables)
            try:
                pr = result["data"]["repository"]["pullRequest"]
                for conn, cursor, flag in _CONNECTIONS:
                    if not wanted[flag]:
                        continue
                    page = pr[conn]
                    if conn == "reviewThreads":
                        found[conn] += [_thread(n, self._thread_comments(op, n), op) for n in page["nodes"]]
                    else:
                        found[conn] += _items(conn, page["nodes"])
                    wanted[flag] = page["pageInfo"]["hasNextPage"]
                    cursors[cursor] = page["pageInfo"]["endCursor"]
            except (KeyError, TypeError, IndexError, AttributeError, ValidationError) as exc:
                invalid(op, "GitHub returned an invalid conversation", exc)
        return tuple(i for conn, _, _ in _CONNECTIONS for i in found[conn])

    def post_reply(self, repository: str, number: int, item: ConversationItem, body: str) -> str:
        """Reply in a review thread, or post an issue comment quoting a comment's or review's URL."""
        op = "post_reply"
        if item.kind == "thread":
            result = self._graphql(op, _REPLY, {"id": item.id, "body": body}, write=True)
            try:
                return str(result["data"]["addPullRequestReviewThreadReply"]["comment"]["id"])
            except (KeyError, TypeError) as exc:
                raise ProviderError(FailureCode.RESPONSE_UNKNOWN, op, str(result)[:200], retry_safe=False) from exc
        endpoint = f"{repo(repository)}/issues/{number}/comments"
        posted = self._api(op, "POST", endpoint, body={"body": f"> {item.url}\n\n{body}"}, write=True)
        try:
            return str(posted["node_id"])
        except (KeyError, TypeError) as exc:
            raise ProviderError(FailureCode.RESPONSE_UNKNOWN, op, "gh returned no id", retry_safe=False) from exc

    def resolve_thread(self, thread_id: str) -> bool:
        """Resolve one review thread; True only when GitHub acknowledges it resolved."""
        result = self._graphql("resolve_thread", _RESOLVE, {"id": thread_id}, write=True)
        if not isinstance(result, dict) or result.get("errors"):
            raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "resolve_thread", str(result)[:200], retry_safe=False)
        try:
            return result["data"]["resolveReviewThread"]["thread"]["isResolved"] is True
        except KeyError, TypeError:
            return False
