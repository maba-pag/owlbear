class ClassFetcher:
    SAFE_REFSPEC = "refs/remotes/origin/main:refs/remotes/origin/main"
    UNSAFE_REFSPEC = "refs/remotes/origin/main:refs/heads/main"

    def safe_fetch(self, repository):
        return self._git(repository, "fetch", "--refmap=", "origin", self.SAFE_REFSPEC)

    def unsafe_fetch(self, repository):
        return self._git(repository, "fetch", "--refmap=", "origin", self.UNSAFE_REFSPEC)
