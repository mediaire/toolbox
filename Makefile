# no buildin rules and variables
MAKEFLAGS =+ -rR --warn-undefined-variables

IMAGE_BASE_NAME = mediaire_toolbox
IMAGE_TAG_LATEST = latest
IMAGE_TAG = $(shell git describe --tags --always --dirty)

build:
	docker build -t $(IMAGE_BASE_NAME):$(IMAGE_TAG) \
	             -t $(IMAGE_BASE_NAME):$(IMAGE_TAG_LATEST) \
	             -f Dockerfile .

push:
	docker push $(IMAGE_BASE_NAME):$(IMAGE_TAG)
	docker push $(IMAGE_BASE_NAME):$(IMAGE_TAG_LATEST)

run:
	docker run $(IMAGE_BASE_NAME):$(IMAGE_TAG)

shell:
	docker run -it $(IMAGE_BASE_NAME):$(IMAGE_TAG) sh

test:
	docker run $(IMAGE_BASE_NAME):$(IMAGE_TAG) nosetests tests

