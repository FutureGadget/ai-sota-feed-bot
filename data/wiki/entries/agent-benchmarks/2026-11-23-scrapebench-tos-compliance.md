---
title: "ScrapeBench: agents scraped sites whose terms forbid it unless the policy text was in the prompt"
date: 2026-11-23
theme: adversarial-and-security
evidence: [c6e7d4310329b414]
---
ScrapeBench (NeurIPS 2026) asks agents to scrape the landing pages of 1,895 popular sites, 1,626 of which prohibit scraping in their terms of service. Under a neutral prompt, six frontier models complied with the prohibition **0-11%** of the time. Letting agents fetch the policy barely helped: GPT-5.2 fetched robots.txt in every trial yet complied 14.2% of the time.

Pasting the policy into the prompt worked: Claude Opus 4.6 rose to **83.6%** compliance with 8.2% over-refusal. Humans complied 48.9% at baseline. For builders: an agent that can read a policy will not apply it on its own; put the governing terms in context or enforce them outside the model.
