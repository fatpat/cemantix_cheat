.PHONY: build start search

CACHE=$(shell pwd)/cache.json

$(CACHE):
	touch $(CACHE)

build:
	docker build . -t cemantix

start: $(CACHE)
	docker run --rm -it -v $(CACHE):/cache.json cemantix --cache /cache.json --op start

search: $(CACHE)
	docker run --rm -it -v $(CACHE):/cache.json cemantix --cache /cache.json --op search

fill_cache: $(CACHE)
	docker run --rm -it -v $(CACHE):/cache.json cemantix --cache /cache.json --op fill_cache
