def _git(*arguments):
    return arguments


def dynamic_fetch(repository, refspec):
    return _git(repository, "fetch", "--refmap=", "origin", refspec)


def subscript_fetch(repository, specs):
    return _git(repository, "fetch", "--refmap=", "origin", specs["refspec"])
