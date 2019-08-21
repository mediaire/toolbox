#!/bin/sh

# use deploy keys
gitlab_hostname=$(echo "${CI_REPOSITORY_URL}" | sed -e 's|https\?://gitlab-ci-token:.*@||g' | sed -e 's|/.*||g')
ssh-keyscan "${gitlab_hostname}" >> ~/.ssh/known_hosts
chmod 644 ~/.ssh/known_hosts

# use ssh as gitlab remote
url_host=$(echo "${CI_REPOSITORY_URL}" | sed -e 's|https\?://gitlab-ci-token:.*@|ssh://git@|g')
git remote set-url --push origin "${url_host}"
git config user.email 'dummy@email.com'
git config user.name 'automatic_version_bot'

# in ci, git is in headless mode, thus checkout to head
git checkout $CI_COMMIT_REF_NAME
git pull origin $CI_COMMIT_REF_NAME

# get last commit message
commit_message=$(git log -1 --pretty=%B)

RELEASE_TYPE="patch"

case "$commit_message" in
    *"[MAJOR]"*) RELEASE_TYPE="major"
    ;;
    *"[MINOR]"*) RELEASE_TYPE="minor"
    ;;
    *"[PATCH]"*) RELEASE_TYPE="patch"
    ;;
esac

export $RELEASE_TYPE