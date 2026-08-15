def _git(*arguments, **keywords):
    return arguments, keywords


def unknown_control_fetch(update_head_ok):
    return _git("fetch", "--refmap=", "origin", update_head_ok=update_head_ok)
