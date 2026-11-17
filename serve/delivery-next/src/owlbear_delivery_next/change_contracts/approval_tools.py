"""A worker requests the owner's approval of the protected change Delivery reads itself."""

from owlbear_delivery_next.change_contracts.tool_types import Args, Spec, bounded

LABEL = "configuration-approval"
DIFF = "\n\nThe protected change:\n"


class RequestApproval(Args):
    """Only the reason comes from the worker; Delivery supplies the change and the options."""

    why: str = bounded(
        2000,
        "Why this configuration change is needed for the approved work",
        "The new package needs its tests included in CI.",
    )


REQUEST = Spec(
    "request_approval",
    "Request approval of the current committed lint, format, CI or hook configuration change. Delivery reads "
    "and shows the whole change to the owner. Your step ends and resumes with the answer or a refusal.",
    RequestApproval,
    "ask",
)


def offered(role: str, *, judging: bool = False) -> bool:
    """Only code-producing workers request configuration approval."""
    return role in {"builder", "test-curator"} and not judging
