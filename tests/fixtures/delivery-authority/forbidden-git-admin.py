def write_delivery_artifact(repository, change_id):
    return repository / ".git" / "worktrees" / change_id
