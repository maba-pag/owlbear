class ScopedFetcher:
    def safe_fetch(self, repository, target_ref):
        refspec = f"refs/remotes/origin/main:refs/remotes/origin/{target_ref}"
        return self._git(repository, "fetch", "--refmap=", "origin", refspec)

    def unsafe_fetch(self, repository, target_ref):
        refspec = f"refs/remotes/origin/main:refs/heads/{target_ref}"
        return self._git(repository, "fetch", "--refmap=", "origin", refspec)
