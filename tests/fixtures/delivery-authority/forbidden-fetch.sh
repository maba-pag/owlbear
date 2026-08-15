#!/bin/sh
# shellcheck disable=SC2086
git -C $WORKTREE fetch -u origin refs/remotes/origin/main:refs/heads/main
git fetch origin main:main
git fetch origin \
    HEAD:HEAD
