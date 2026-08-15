import subprocess


def _git(*arguments):
    return arguments


class ForbiddenFetcher:
    def fetch(self, repository, target_ref):
        return self._git(
            repository,
            "fetch",
            "--update-head-ok",
            "origin",
            f"refs/remotes/origin/main:refs/heads/{target_ref}",
        )

    def forward_fetch(self, repository, arguments):
        return self._git(repository, "fetch", *arguments)


def forbidden_module_fetch(repository, target_ref):
    return _git(
        repository,
        "fetch",
        "--update-head-ok",
        "origin",
        f"refs/remotes/origin/main:refs/heads/{target_ref}",
    )


def forbidden_subprocess_fetch(target_ref):
    return subprocess.run(
        [
            "git",
            "fetch",
            "--update-head-ok",
            "origin",
            f"refs/remotes/origin/main:refs/heads/{target_ref}",
        ],
        check=False,
    )


def forbidden_bare_destination(repository, target_ref):
    return _git(
        repository,
        "fetch",
        "--refmap=",
        "origin",
        f"refs/remotes/origin/main:{target_ref}",
    )
