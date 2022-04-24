.PHONY: build start search

build:
	docker build . -t cemantix

start:
	docker run --rm -it -v $(shell pwd)/cache.json:/cache.json cemantix --cache /cache.json --op start

search:
	docker run --rm -it -v $(shell pwd)/cache.json:/cache.json cemantix --cache /cache.json --op search
