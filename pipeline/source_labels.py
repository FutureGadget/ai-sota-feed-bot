"""Reader-facing names for feed source slugs (pages and email)."""

from __future__ import annotations

import re

SOURCE_NAMES = {
    "arxiv_cs_ai": "arXiv cs.AI",
    "arxiv_cs_lg": "arXiv cs.LG",
    "arxiv_cs_cl": "arXiv cs.CL",
    "paperswithcode_latest": "Papers with Code",
    "openai_blog": "OpenAI Blog",
    "anthropic_newsroom": "Anthropic Newsroom",
    "anthropic_engineering": "Anthropic Engineering",
    "anthropic_research": "Anthropic Research",
    "huggingface_blog": "Hugging Face Blog",
    "nvidia_blog": "NVIDIA Blog",
    "google_ai_blog": "Google AI Blog",
    "google_cloud_blog": "Google Cloud Blog",
    "google_deepmind_blog": "Google DeepMind Blog",
    "aws_ml_blog": "AWS ML Blog",
    "vllm_blog": "vLLM Blog",
    "vllm_releases": "vLLM Releases",
    "triton_releases": "Triton Releases",
    "llamaindex_releases": "LlamaIndex Releases",
    "langgraph_releases": "LangGraph Releases",
    "openai_codex_releases": "OpenAI Codex Releases",
    "claude_code_releases": "Claude Code Releases",
    "claude_agent_sdk_python_releases": "Claude Agent SDK Releases",
    "claude_blog": "Claude Blog",
    "cloudflare_blog": "Cloudflare Blog",
    "databricks_blog": "Databricks Blog",
    "hackernews_ai": "Hacker News AI",
    "infoq_ai_ml": "InfoQ AI/ML",
    "simon_willison": "Simon Willison",
    "latent_space": "Latent Space",
    "langchain_blog": "LangChain Blog",
    "search_agent_engineering_news": "Agent Engineering News",
    "search_llm_ops_news": "LLM Ops News",
    "search_cn_open_weight_labs": "CN Open-Weight Lab coverage",
}
SOURCE_ACRONYMS = {"ai", "ml", "llm", "aws", "api", "sdk", "gpu"}


def source_name(slug: str) -> str:
    """``hackernews_ai`` -> ``Hacker News AI``; unknown slugs are title-cased."""
    s = (slug or "").strip()
    if not s:
        return "unknown"
    if s in SOURCE_NAMES:
        return SOURCE_NAMES[s]
    return " ".join(
        w.upper() if w.lower() in SOURCE_ACRONYMS else w[:1].upper() + w[1:]
        for w in re.split(r"[_\s]+", s)
        if w
    )
