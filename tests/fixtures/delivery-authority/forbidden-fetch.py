class ForbiddenFetcher:
    def fetch(self, repository, target_ref):
        return self._git(
            repository,
            "fetch",
            "--update-head-ok",
            "origin",
            f"refs/remotes/origin/main:refs/heads/{target_ref}",
        )
