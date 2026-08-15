def _git(*arguments, **keywords):
    return arguments, keywords


def boolean_fetch(target_ref):
    update_head_ok = True
    return _git(
        "fetch",
        "--refmap=",
        "origin",
        f"refs/remotes/origin/main:refs/remotes/origin/{target_ref}",
        update_head_ok=update_head_ok,
    )
