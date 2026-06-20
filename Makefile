.PHONY: collect digest

collect:
	python collectors/collect.py

digest:
	python pipeline/build_digest.py
