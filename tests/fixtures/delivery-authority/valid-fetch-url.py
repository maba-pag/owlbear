def _git(*arguments):
    return arguments


def fetch_from_url(repository):
    return _git(repository, "fetch", "--refmap=", "https://example.com/repository.git", "main")
