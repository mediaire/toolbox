#!/bin/sh
TITLE_CHECK=false
echo "$CI_MERGE_REQUEST_TITLE"
case "$CI_MERGE_REQUEST_TITLE" in
    *"[MAJOR]"*) TITLE_CHECK=true
    ;;
    *"[MINOR]"*) TITLE_CHECK=true
    ;;
    *"[PATCH]"*) TITLE_CHECK=true
    ;;
esac
if ! $TITLE_CHECK; then
    echo "Merge request format is wrong, add [MAJOR], [MINOR] or [PATCH] to title"
    exit 1
else
    echo "Test passed"
    exit 0
fi
