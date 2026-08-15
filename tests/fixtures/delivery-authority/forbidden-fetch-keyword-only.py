def _git(*arguments, **keywords):
    return arguments, keywords


def keyword_only_fetch(target_ref):
    return _git(
        "fetch",
        "--refmap=",
        refspec=f"refs/remotes/origin/main:refs/heads/{target_ref}",
    )
