def _git(*arguments, **keywords):
    return arguments, keywords


def keyword_fetch(repository, target_ref):
    return _git(
        repository,
        "fetch",
        "--refmap=",
        "origin",
        refspec=f"refs/remotes/origin/main:refs/heads/{target_ref}",
    )
