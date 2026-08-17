import os as operating_system
import subprocess as process
from subprocess import Popen, check_output
from subprocess import run as execute


def _git(*arguments):
    return arguments


def alias_run(target_ref):
    return process.run(
        ["git", "fetch", "--update-head-ok", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"],
        check=False,
    )


def imported_run(target_ref):
    return execute(
        ["git", "fetch", "--update-head-ok", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"],
        check=False,
    )


def output_fetch(target_ref):
    return check_output(
        ["git", "fetch", "--update-head-ok", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"]
    )


def popen_fetch(target_ref):
    return Popen(["git", "fetch", "--update-head-ok", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"])


def check_call_fetch(target_ref):
    return process.check_call(["git", "fetch", "-u", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"])


def shell_fetch(target_ref):
    return operating_system.system(  # noqa: S605
        f"git fetch --update-head-ok origin refs/remotes/origin/main:refs/heads/{target_ref}"
    )


def shell_popen_fetch(target_ref):
    return operating_system.popen(  # noqa: S605
        f"git fetch --update-head-ok origin refs/remotes/origin/main:refs/heads/{target_ref}"
    )


class HelperAlias:
    def fetch(self, target_ref):
        return self.execute_git_command(
            "fetch", "--update-head-ok", "origin", f"refs/remotes/origin/main:refs/heads/{target_ref}"
        )
