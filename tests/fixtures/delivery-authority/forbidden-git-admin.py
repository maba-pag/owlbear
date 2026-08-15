from pathlib import Path


def write_delivery_artifact(repository, change_id):
    return repository / ".git" / "worktrees" / change_id


def write_legacy_artifact(repository, change_id):
    return repository / ".git/worktrees" / change_id


def write_git_dir_artifact(change_id):
    return "$GIT_DIR/worktrees/" + change_id


def write_common_dir_artifact(change_id):
    return "$GIT_COMMON_DIR/worktrees/" + change_id


def write_path_constructor_artifact(change_id):
    return Path(".git", "worktrees", change_id)


def write_named_admin_artifact(git_admin_dir, change_id):
    return git_admin_dir / "worktrees" / change_id
