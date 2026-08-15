class ForbiddenFetcher:
    def fetch(self, repository, target_ref):
        return self._git(
            repository,
            "fetch",
            "--update-head-ok",
            "origin",
            f"{target_ref}:refs/heads/main",
        )
