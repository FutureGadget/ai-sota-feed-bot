# Daily AI SOTA Digest - 2026-02-15

Focus: AI Platform Engineering

## 1. Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical Speech Applications
- Type: paper | Source: arxiv_cs_lg
- URL: http://arxiv.org/abs/2602.12241v1
- Score: 9.03 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, latency, cost
- Why it matters: Streaming ASR with bounded latency via sliding-window attention enables real-time agent voice I/O on edge; critical for agentic harness deployment patterns.

## 2. Leading Inference Providers Cut AI Costs by up to 10x With Open Source Models on NVIDIA Blackwell
- Type: news | Source: nvidia_blog
- URL: https://blogs.nvidia.com/blog/inference-open-source-models-blackwell-reduce-cost-per-token/
- Score: 6.217 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, cost, agent
- Why it matters: Generic hardware marketing lacking technical depth on inference optimization, agent serving patterns, or deployment integration.

## 3. Is Your AI Agent Safe?
- Type: news | Source: hackernews_ai
- URL: https://agentshield.live/
- Score: 5.29 | Reliability: 1.0 | Maturity: research
- Tags: agent
- Why it matters: Likely impact on agent workflows and platform decisions.

## 4. Show HN: AgentScore – Lighthouse for AI Agents
- Type: news | Source: hackernews_ai
- URL: https://github.com/xiongallen40-design/agentscore
- Score: 5.288 | Reliability: 1.0 | Maturity: research
- Tags: agent
- Why it matters: Likely impact on agent workflows and platform decisions.

## 5. v0.16.0
- Type: release | Source: vllm_releases
- URL: https://github.com/vllm-project/vllm/releases/tag/v0.16.0
- Score: 15.107 | Reliability: 1.0 | Maturity: production-ready
- Tags: serving, throughput, optimization, quantization, triton
- Why it matters: Async+pipeline parallelism (30.8% throughput), speculative decoding structured outputs, RLHF infra improvements critical for production coding-agent serving at scale.

## 6. v0.15.0
- Type: release | Source: vllm_releases
- URL: https://github.com/vllm-project/vllm/releases/tag/v0.15.0
- Score: 14.604 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, throughput, optimization, quantization, triton
- Why it matters: Inference serving infrastructure gains critical production hardening: async scheduling+pipeline parallelism, speculative decoding expansions, Mamba prefix caching (~2x speedup), FP4 optimizations (65% faster on Blackwell), and distributed fixes enabling reliable multi-modal coding agent deployment.

## 7. Release 2.59.0 corresponding to NGC container 25.06
- Type: release | Source: triton_releases
- URL: https://github.com/triton-inference-server/server/releases/tag/v2.59.0
- Score: 11.3 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, latency, throughput, agent, triton
- Why it matters: Inference serving release notes with minor ensemble perf tweaks; not relevant to agentic coding automation or full SDLC delivery loops.

## 8. Agentic Test-Time Scaling for WebAgents
- Type: paper | Source: arxiv_cs_ai
- URL: http://arxiv.org/abs/2602.12276v1
- Score: 7.234 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, agent
- Why it matters: Practical inference-time scaling technique for multi-step agents with measurable token efficiency gains and deployable uncertainty signals for reliability.

## 9. Scaling Verification Can Be More Effective than Scaling Policy Learning for Vision-Language-Action Alignment
- Type: paper | Source: arxiv_cs_ai
- URL: http://arxiv.org/abs/2602.12281v1
- Score: 6.834 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, benchmark
- Why it matters: Test-time verification scaling for VLA alignment offers deployment patterns applicable to coding agents: hierarchical verification, rephrasing diversity, and compute-inference tradeoffs.

## 10. Amortized Molecular Optimization via Group Relative Policy Optimization
- Type: paper | Source: arxiv_cs_lg
- URL: http://arxiv.org/abs/2602.12162v1
- Score: 6.621 | Reliability: 1.0 | Maturity: production-ready
- Tags: inference, optimization
- Why it matters: Likely impact on inference, optimization workflows and platform decisions.

## 11. Harness engineering: leveraging Codex in an agent-first world
- Type: news | Source: openai_blog
- URL: https://openai.com/index/harness-engineering
- Score: 4.871 | Reliability: 1.0 | Maturity: research
- Tags: agent
- Why it matters: Likely impact on agent workflows and platform decisions.

## 12. GPT-5 lowers the cost of cell-free protein synthesis
- Type: news | Source: openai_blog
- URL: https://openai.com/index/gpt-5-lowers-protein-synthesis-cost
- Score: 4.638 | Reliability: 1.0 | Maturity: research
- Tags: cost
- Why it matters: Likely impact on cost workflows and platform decisions.
