#!/bin/sh
git -C /tmp/repo fetch -u origin refs/remotes/origin/main:refs/heads/main
git fetch origin main:main
git fetch origin \
	HEAD:HEAD