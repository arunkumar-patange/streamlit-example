# make image
# make start

SHELL := /bin/bash
HIDE ?= @
DOCKER_IMAGE ?= brain/streamlit
DOCKER_CONTAINER ?= streamlit
VOLUME ?=-v $(PWD):/brain/src -v $(DOCKER_CONTAINER)-venv:/venv
DOCKER_ENV ?=--rm -it
ENVIRONMENT ?= development

-include ./docker/registry.mk
-include ./docker/utils.mk
-include ./docker/docs.mk
-include ./docker/deploy.mk

.PHONY: image test lint docs start

build:
	$(HIDE)docker build -f Dockerfile -t $(DOCKER_IMAGE) $(PWD)
	-$(HIDE)$(MAKE) install

install:
	$(HIDE)docker run -it --rm $(VOLUME) $(DOCKER_IMAGE) ./docker/setup.sh

start:
	$(HIDE)echo 'env `cat .env|xargs` streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.fileWatcherType=none'
	$(HIDE)docker run -it --rm -v${PWD}:/app -p8501:8501 --entrypoint=/bin/bash brain/streamlit
