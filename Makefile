.PHONY: collect digest publish

collect:
	python collectors/collect.py

digest:
	python pipeline/build_digest.py

publish:
	python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot
