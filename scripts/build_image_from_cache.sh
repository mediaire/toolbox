#! /bin/bash

if [ -z "$1" ] || [ -z "$2" ] || [ -z "${3}" ] || [ -z "${4}" ]; then
    echo "build.sh <project_name> <registry> <image git tag> <docker target>"
fi

PROJECT_NAME=$1
REGISTRY=$2
IMAGE_GIT_TAG=$3
TARGET=$4

IMAGE_BASE_NAME=${REGISTRY}/development/mdbrain/${PROJECT_NAME}
CI_IMAGE_BASE_NAME=${REGISTRY}/ci/mdbrain/${PROJECT_NAME}

function build_runenv (){
    docker build \
        --cache-from ${1}:runenv \
		--target runenv \
		-t ${1}:runenv \
	    -f Dockerfile .
}

function build_dev (){
    docker build \
        --cache-from ${1}:runenv \
        --cache-from ${1}:dev \
		--target dev \
		-t ${1}:dev \
        -t ${1}:${2}-dev \
	    -f Dockerfile .
}

function build_builder (){
    docker build \
        --cache-from ${1}:runenv \
        --cache-from ${1}:dev \
        --cache-from ${1}:builder \
		--target builder \
		-t ${1}:builder \
	    -f Dockerfile .
}

function build_release_test (){
    docker build \
        --cache-from ${1}:runenv \
        --cache-from ${1}:dev \
        --cache-from ${1}:builder \
		--target release_test \
		-t ${1}:release_test \
	    -f Dockerfile .
}

function build_release (){
    docker build \
        --cache-from ${1}:runenv \
        --cache-from ${1}:dev \
        --cache-from ${1}:builder \
        --cache-from ${1}:release \
		--target release \
		-t ${1}:release \
        -t ${2}:${3} \
	    -f Dockerfile .
}

if [ "${TARGET}" == "dev" ]; then
    # pull cache
    docker pull ${CI_IMAGE_BASE_NAME}:runenv || true
    docker pull ${CI_IMAGE_BASE_NAME}:dev || true

    # build cache
    build_runenv ${CI_IMAGE_BASE_NAME}
    build_dev ${CI_IMAGE_BASE_NAME} ${IMAGE_GIT_TAG}

    # update cache
    docker push ${CI_IMAGE_BASE_NAME}:runenv
    docker push ${CI_IMAGE_BASE_NAME}:dev
fi

if [ "${TARGET}" == "release_test" ]; then
    IMAGE_TAG=${IMAGE_GIT_TAG}
    # pull cache
    docker pull ${CI_IMAGE_BASE_NAME}:runenv || true
    docker pull ${CI_IMAGE_BASE_NAME}:dev || true
    docker pull ${CI_IMAGE_BASE_NAME}:builder || true

    # build cache
    build_runenv ${CI_IMAGE_BASE_NAME}
    build_dev ${CI_IMAGE_BASE_NAME} ${IMAGE_GIT_TAG}
    build_builder ${CI_IMAGE_BASE_NAME}
    build_release_test ${CI_IMAGE_BASE_NAME}

    # update cache
    docker push ${CI_IMAGE_BASE_NAME}:builder
fi

if [ "${TARGET}" == "release" ]; then
    IMAGE_TAG=${IMAGE_GIT_TAG}
    # pull cache
    docker pull ${CI_IMAGE_BASE_NAME}:runenv || true
    docker pull ${CI_IMAGE_BASE_NAME}:dev || true
    docker pull ${CI_IMAGE_BASE_NAME}:builder || true
    docker pull ${CI_IMAGE_BASE_NAME}:release || true

    # build cache
    build_runenv ${CI_IMAGE_BASE_NAME}
    build_dev ${CI_IMAGE_BASE_NAME} ${IMAGE_GIT_TAG}
    build_builder ${CI_IMAGE_BASE_NAME}
    build_release ${CI_IMAGE_BASE_NAME} ${IMAGE_BASE_NAME} ${IMAGE_GIT_TAG}

    # update cache
    docker push ${CI_IMAGE_BASE_NAME}:builder
    docker push ${CI_IMAGE_BASE_NAME}:release
fi