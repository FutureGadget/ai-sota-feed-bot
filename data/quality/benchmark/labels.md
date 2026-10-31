# Benchmark labels (provisional)

Assistant-authored labels for owner review. Edit `items.json` after
correcting a row, then rerun the benchmark.

| id | slice | source | title | expected | fine | note |
|---|---|---|---|---|---|---|
| bench-001 | first_party_engineering | anthropic_engineering | Redesigning source control at Anthropic | keep | must_read | First-party engineering deep dive on source control at a frontier lab. |
| bench-002 | first_party_engineering | cloudflare_blog | Cutting our inference bill by 68% by being obsessive about optimization | keep | must_read | Concrete inference cost optimization with numbers; direct platform-engineer fit. |
| bench-003 | first_party_engineering | vllm_blog | GLM-5.3 Optimizations, Part 2: PCP, DCP, and Hybrid HiSparse on 16 H200s | keep | must_read | Deep inference serving optimization detail (PCP, DCP, HiSparse) with hardware context. |
| bench-004 | first_party_engineering | huggingface_blog | How Specializing the Vocabulary of SLMs Can Cut Inference Cost by 77% in Real Applications | keep | useful | Concrete inference-cost technique with a measured result. |
| bench-005 | first_party_engineering | claude_dev_blog | How the Claude Code team does code review | keep | useful | Engineering practice from the team building a coding agent. |
| bench-006 | first_party_engineering | google_cloud_blog | Who judges the judge? Three helpful ways to audit your LLM evaluators | keep | must_read | Eval auditing guidance; directly relevant to the judge layer we are building. |
| bench-007 | first_party_marketing | openai_blog | ChatGPT Ads expands to 26 new countries as over 100,000 advertisers have used the platform | drop | junk | Ad-market expansion; no engineering substance for the platform-engineer lens. |
| bench-008 | first_party_marketing | openai_blog | How AT&T is rethinking in-house legal work with OpenAI | drop | junk | Customer story about legal work; no reusable platform mechanism. |
| bench-009 | first_party_marketing | openai_blog | OpenAI and Poland’s NASK partner to advance AI safety and security | drop | junk | Government partnership announcement; no technical detail. |
| bench-010 | first_party_marketing | anthropic_newsroom | 2026 Usage Policy update | drop | junk | Policy update; not engineering content. |
| bench-011 | first_party_marketing | anthropic_newsroom | Singapore office and government MOU \| Anthropic | drop | junk | Office/MOU announcement; no engineering content. |
| bench-012 | first_party_marketing | modal_blog | Modal crosses $1B in Annualized Run Rate and raises $750M Series D | drop | junk | Funding/ARR announcement; company news, not engineering. |
| bench-013 | first_party_marketing | openai_blog | OpenAI models are coming to Google Cloud | keep | useful | Hard positive: a distribution announcement that changes where platform teams can run the model. |
| bench-014 | first_party_marketing | anthropic_newsroom | Donating Agent Skills to the Agentic AI Foundation | keep | useful | Hard positive: a corporate announcement about agent skills that is directly relevant to agent builders. |
| bench-015 | practitioner_analysis | simon_willison | Introducing Kimi K3.1 Pro | keep | useful | Launch analysis with model details from a trusted practitioner. |
| bench-016 | practitioner_analysis | latent_space | [AINews] Kimi 3.1 Pro 104BA-2.8T: Fable-5.1-Class Open Weights narrows Closed-AI lead to 1 month... and Pro Highspeed API with 2-3× speed | keep | must_read | Detailed open-weight model analysis with benchmark and pricing context. |
| bench-017 | practitioner_analysis | hamel_husain | How To Use Decision Models for Evals | keep | must_read | Directly relevant to the Jev/decision-model judge design. |
| bench-018 | practitioner_analysis | infoq_ai_ml | Google’s Data Agent Kit Hits GA, Splitting Agent Guardrails Between Skills and IAM | keep | useful | Agent platform release with an architecture angle (skills vs IAM guardrails). |
| bench-019 | practitioner_analysis | simon_willison | Today's PHP Security Release, and How We're Strengthening PHP Security | drop | filler | Off-mission PHP security release; no AI/agent engineering substance. |
| bench-020 | practitioner_analysis | simon_willison | Panache — RTS Belle Époque pour mobile | drop | junk | Off-mission game/RTS post; no AI platform relevance. |
| bench-021 | search_seo | search_agent_engineering_news | Claude Code vs Codex vs Copilot: 2026 Comparison | drop | junk | SEO comparison listicle; no original engineering evidence. |
| bench-022 | search_seo | search_agent_engineering_news | 7 Best Claude Code Alternatives for CLI Agentic Coding | drop | junk | Ranked listicle; no substantive mechanism. |
| bench-023 | search_seo | search_agent_engineering_news | Best AI Coding Agent in 2026: Codex, Claude Code, Cursor, or OpenCode? | drop | junk | Buyer's-guide listicle; not platform engineering. |
| bench-024 | search_seo | search_cn_open_weight_labs | What Is DeepSeek? Open-Weight AI Models Explained | drop | junk | Explainer/SEO content; no new information. |
| bench-025 | search_seo | search_cn_open_weight_labs | DeepSeek API Key Setup: V4.1 Flash in 13 Steps [2026] | drop | junk | Step-by-step setup SEO; not engineering analysis. |
| bench-026 | search_seo | search_cn_open_weight_labs | DeepSeek Ships a Faster Flash Model and Its Own Search API | keep | useful | Hard positive: a genuine release scoop with a concrete API change. |
| bench-027 | search_business_gossip | search_cn_open_weight_labs | China's Teenage AI Prodigy Leaves Moonshot AI, Denies Moving to U.S. Anthropic | drop | junk | Executive/gossip story; no engineering substance. |
| bench-028 | search_business_gossip | search_cn_open_weight_labs | DeepSeek Raises $15 Billion Ahead of Planned Shanghai IPO | drop | junk | Funding/IPO story; no engineering substance. |
| bench-029 | search_business_gossip | search_cn_open_weight_labs | DeepSeek fires back at U.S.federal agency ban as 'overstretching of the concept of national security' | drop | junk | Policy/market reaction; no engineering substance. |
| bench-030 | search_business_gossip | search_cn_open_weight_labs | DeepSeek Suffers Nearly 5-Hour Outage as China’s AI Boom Fuels Chip Shortage | drop | junk | Outage story without a technical postmortem; not actionable. |
| bench-031 | search_business_gossip | search_cn_open_weight_labs | Alibaba starts selling its Qwen N1 AI glasses in China from $450 | drop | junk | Consumer hardware/PR; off-mission. |
| bench-032 | search_business_gossip | search_cn_open_weight_labs | DeepSeek prices web search for AI agents at $0.75 per 1,000 calls | keep | useful | Hard positive: a concrete API pricing change for agent builders. |
| bench-033 | off_topic_domain | google_deepmind_blog | Accelerating the search for antimicrobial peptides with Google Antigravity | drop | junk | Domain science (antimicrobial peptides); no platform-engineering lesson. |
| bench-034 | off_topic_domain | openai_blog | Using thousands of AI agents to uncover new leads in biological data | drop | filler | Agent use case in biology; interesting, but not platform-engineering guidance. |
| bench-035 | off_topic_domain | arxiv_llm_reliability | IndoNutriQA: An Indonesian Clinical Nutrition Question Answering Benchmark | drop | junk | Clinical nutrition benchmark; off-mission. |
| bench-036 | off_topic_domain | google_deepmind_blog | Beyond tree cover: mapping the world’s forest types | drop | junk | Forest mapping; no agent/platform engineering. |
| bench-037 | off_topic_domain | databricks_blog | Deploy RFD4-Proteina on Databricks | drop | junk | Protein model deployment; domain science, not platform guidance. |
| bench-038 | off_topic_domain | latent_space | AI Is Getting Good at Math. Here’s Why. | drop | junk | Math capability commentary; no platform-engineering mechanism. |
| bench-039 | research | arxiv_agent_systems_research | Muffin - A Shared Memory Buffer for Asynchronous AI Agents | keep | useful | Agent memory architecture with a concrete mechanism. |
| bench-040 | research | arxiv_agent_systems_research | Post-Audit Mirage: Identifiability Limits of Offline Agent Verification | keep | useful | Limits of offline agent verification; relevant to eval design. |
| bench-041 | research | arxiv_cs_ai | Adaptive Skill Granularity for Coding Agents: Runtime Routing and Macro-to-Micro Recovery | keep | useful | Runtime routing and recovery for coding agents; directly relevant. |
| bench-042 | research | arxiv_cs_ai | Causal Chain of Thought: Mitigating Attention Leakage via Context Isolation | keep | useful | Context isolation and attention leakage; relevant to agent reliability. |
| bench-043 | research | arxiv_llm_reliability | When LLMs Forget What They Believe: Characterizing State Integrity Collapse in Long-Horizon Dialogues | keep | useful | Long-horizon state integrity; relevant to agent memory/reliability. |
| bench-044 | research | arxiv_cs_cl | Parameter-Efficient Adaptation of Large Language Models to a Low-Resource Agglutinative Language: A Corpus, Datasets, and a Reproducible Benchmark for the Bashkir Language | drop | filler | Niche low-resource adaptation; not platform/agent engineering. |
| bench-045 | releases | vllm_releases | v0.32.0 | drop | filler | Routine release notes; belongs in the Releases tab, not the brief. |
| bench-046 | releases | claude_code_releases | v2.1.310 | drop | filler | Routine CLI version bump; no standalone engineering insight. |
| bench-047 | releases | langgraph_releases | langgraph==1.2.17 | drop | filler | Routine package release; no standalone engineering insight. |
| bench-048 | releases | openai_codex_releases | 0.164.0-alpha.12 | drop | filler | Alpha release note; no standalone engineering insight. |
| bench-049 | releases | huggingface_blog | Welcome Beam: a 501B open model you can own, customize, and scale | keep | useful | Model release with serving/deployment context; useful to platform teams. |
| bench-050 | releases | vllm_blog | vLLM Delivers Day-0 Support for MiniMax-M3.1-Flash | keep | useful | Serving support for a new model; useful to inference-platform teams. |
| bench-051 | video | ai_native_dev | Caleb Sima: AI Attackers Move at Machine Speed | keep | useful | Long-form interview with concrete attacker mechanics (0-day discovery, token burn, sandbox limits). Tests a transcript-backed video keep. |
| bench-052 | video | ai_native_dev | Your Coding Agent Should Never Hold a Credential | keep | useful | Conference session on agent credential handling and Agent Baseline; concrete security mechanism. |
| bench-053 | video | ai_native_dev | Maria Gorinova: Feedback Loops That Fix Your Codebase | keep | useful | Practitioner talk on feedback loops for coding agents; concrete reliability mechanism. |
| bench-054 | video | ai_native_dev | Harness Engineering: What's Actually New (And What Isn't) | keep | useful | Long-form talk on harness engineering. No companion podcast transcript matched, so this tests the description-only video path. |
| bench-055 | video | ai_native_dev | Automated AI Code Review on GitHub, Set Up in 2 Minutes | drop | junk | Product setup walkthrough; a UI demo with no reusable mechanism. Should drop even with a transcript available. |
| bench-056 | video | ai_native_dev | Dark Factory Considered Harmful? Meet the AI DevCon NYC Speakers | drop | junk | Conference lineup promo spot for AI DevCon NYC; no technical content. |
| bench-057 | video | ai_native_dev | Codeplain at AI DevCon New York: Regenerative Software | drop | junk | Conference promo clip with no reusable engineering detail. |
| bench-058 | video | ai_native_dev | The helicopter-parent model | drop | junk | A Short clip promoting a full episode; a fragment, not evidence. The collector skips /shorts/ before ranking; the rubric must still drop it. |
