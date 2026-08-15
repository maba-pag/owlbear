class ForbiddenFetcher:
    def fetch(self, remote: str, branch: str):
        return self._run_git(
            "fetch",
            "--update-head-ok",
            remote,
            f"refs/heads/{branch}:refs/heads/main",
        )