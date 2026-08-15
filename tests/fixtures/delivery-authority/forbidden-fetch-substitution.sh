#!/bin/sh
target=$(git fetch -u origin main:main)
printf '%s\n' "$target"
