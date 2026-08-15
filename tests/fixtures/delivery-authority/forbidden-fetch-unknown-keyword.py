def _git(*arguments, **keywords):
    return arguments, keywords


def unknown_keyword_fetch(target_ref):
    return _git(
        "fetch",
        "--refmap=",
        "origin",
        ref=f"refs/remotes/origin/main:refs/heads/{target_ref}",
    )
