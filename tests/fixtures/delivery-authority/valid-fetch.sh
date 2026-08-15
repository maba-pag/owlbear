#!/bin/sh
git fetch --refmap= origin main --no-tags | sort -u
git fetch https://example.com/repository.git
echo "git fetch -u origin refs/remotes/origin/main:refs/heads/main"