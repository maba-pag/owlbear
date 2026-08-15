refspec = "refs/remotes/origin/main:refs/remotes/origin/main"


class ScopedFetcher:
    def safe_fetch(self, repository):
        return self._git(repository, "fetch", "--refmap=", "origin", refspec)

    def unsafe_fetch(self, repository):
        refspec = "refs/remotes/origin/main:refs/heads/main"
        return self._git(repository, "fetch", "--refmap=", "origin", refspec)
