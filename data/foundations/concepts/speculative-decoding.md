---
slug: speculative-decoding
title: "How does speculative decoding speed up LLM inference?"
question: "How does speculative decoding speed up LLM inference?"
summary: "Speculative decoding drafts several tokens cheaply, then verifies them in one parallel pass through the target model — cutting decode latency without changing the output distribution, as long as the draft's guesses are good enough to pay for themselves."
status: active
cluster: operations
updated: 2026-10-06
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [speculative-decoding, agent-latency, agent-cost]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: leviathan-2023-speculative-decoding
    kind: theory-paper
    title: "Fast Inference from Transformers via Speculative Decoding"
    url: "https://arxiv.org/abs/2211.17192"
    added: 2026-07-15
    note: "Introduces speculative decoding and proves the accept/reject scheme reproduces the target model's output distribution exactly, so the speedup carries no quality trade-off."
  - id: chen-2023-speculative-sampling
    kind: theory-paper
    title: "Accelerating Large Language Model Decoding with Speculative Sampling"
    url: "https://arxiv.org/abs/2302.01318"
    added: 2026-07-15
    note: "Independently formalizes speculative sampling with the same modified-rejection-sampling correctness argument as Leviathan et al."
  - id: li-2024-eagle
    kind: theory-paper
    title: "EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty"
    url: "https://arxiv.org/abs/2401.15077"
    added: 2026-07-15
    note: "Drafts from the target model's own hidden-state features with a lightweight head instead of an independent small model. Higher acceptance rates made speculation a practical serving default."
  - id: vllm-eagle3-amd-instinct-2026
    kind: story
    sid: f0c08e4beff850db
    title: "EAGLE-3 Speculative Decoding on AMD Instinct GPUs: Training and Serving with vLLM and AMD Quark"
    added: 2026-07-15
    note: "EAGLE-3 in a real vLLM serving stack on AMD Instinct GPUs: 2.00x throughput on Kimi-K2.5 and 1.79x on MiniMax-M2.5. Shows the pattern ships across accelerator vendors. Vendor-reported."
  - id: modal-decagon-specdec-2026
    kind: story
    sid: 62173e9d865bdec2
    title: "Achieve state-of-the-art inference latencies with speculative decoding"
    added: 2026-07-15
    note: "Modal and Decagon production write-up treating speculative decoding as workload-specific draft/target tuning, not a flip-a-switch default."
  - id: nvidia-dflash-blackwell-2026
    kind: story
    sid: 99bd515fd5fd8083
    title: "Boost Inference Performance up to 15x on NVIDIA Blackwell Using DFlash Speculative Decoding"
    added: 2026-07-15
    note: "DFlash on NVIDIA Blackwell reports up to 15x when the draft/verify pair is co-designed with the accelerator. A vendor ceiling number, not a typical one; compare roughly 1.8-2x in less specialized stacks."
---

## Builder consequence
Decode dominates an agent's wall-clock, and by default it is strictly sequential: one token in, one full forward pass, one token out, repeated for every token of every turn. Speculative decoding is the one latency lever that cuts that sequential cost without touching model weights, retraining anything end-to-end, or trading away answer quality — which makes it worth understanding as a mechanism you can reason about, not just a serving flag you flip and hope.

## Short answer
A cheap draft process proposes several tokens ahead of where the target model has actually decoded. The target model then checks all of those guesses in a single forward pass instead of one at a time. Tokens the target model would have produced anyway are accepted for free; the first guess it disagrees with is thrown out and resampled correctly from there. The accept/reject math guarantees the final output has exactly the same distribution as running the target model alone — the speedup comes from turning a sequential dependency into a parallel check, not from approximating the model.

## Builder model
Decode at typical serving batch sizes is memory-bandwidth-bound, not compute-bound: most of a decode step is spent streaming model weights through the GPU, with FLOPs to spare. Speculative decoding spends that spare compute. Verifying several draft tokens in one forward pass costs about the same wall-clock as producing a single token normally, because the bottleneck — memory traffic — barely grows while the extra parallel compute is nearly free, right up until the batch gets large enough to saturate the chip.

## Mechanism
One decode cycle has three steps:

- **Draft.** A cheap process — a much smaller separate model, or a lightweight head trained alongside the target model — autoregressively proposes several candidate tokens ahead of the current position.
- **Verify.** The target model runs a single forward pass over the drafted tokens together, producing next-token probabilities at every position at once. This is what the parallelism buys: a transformer's forward pass is inherently parallel across positions — only its own token-by-token *sampling* was ever sequential.
- **Accept or reject.** Walk the candidates left to right. Accept a draft token with probability `min(1, p_target(x) / q_draft(x))`. At the first token the check fails, discard every draft token after it and resample that position from the corrected residual distribution, then start the next draft cycle from there.

The engineering advances that made this a serving default (EAGLE and its EAGLE-3 successor, now served in vLLM on AMD Instinct at about 2x throughput) are almost entirely in the draft step: instead of an independently trained small model, they train a lightweight head to predict the target model's own next hidden-state features autoregressively. Because the draft is derived from the target's own internal state rather than a separately trained approximation, its guesses correlate far more with what the target model would actually choose, which is what raises the acceptance rate high enough to pay for the extra verify pass.

## Math intuition
The correctness argument is a modified rejection sampling scheme. For a draft distribution `q` and target distribution `p`, accept a drafted token `x` with probability `min(1, p(x)/q(x))`. If rejected, resample from the residual distribution `max(0, p(x) - q(x))`, renormalized. Summing the accept branch and the reject-then-resample branch over all possible tokens reproduces `p(x)` exactly, regardless of what `q` is — the draft can be a bad guesser and the math still holds, it just accepts less often. The draft is *free information*, never *different information*: a bad draft costs you speed, not correctness.

The speed argument follows from the memory-bound builder model above. If one decode step costs time `T` largely independent of small compute increases, then verifying `k` draft tokens in one step still costs roughly `T`, not `k · T`. Accepting an average of `α · k` tokens per verify step (`α` = acceptance rate) turns `α · k` sequential steps into one, so the achievable speedup tracks `1 + α · k` — until batch size grows enough that the GPU becomes compute-bound and the "`T` regardless of `k`" assumption stops holding.

## How to apply
- Measure acceptance rate on your own traffic before trusting any vendor's throughput multiplier. Low-entropy, structured output — code, JSON, repetitive tool-call arguments — accepts at much higher rates than open-ended creative text, so the same technique can be a large win for one agent and a marginal one for another.
- Prefer a feature-level draft head trained alongside the target model (the EAGLE approach) over an off-the-shelf small model as the draft; acceptance rate is the entire economics of the technique.
- Benchmark end-to-end latency and cost per token at your real concurrency, not tokens/sec at one batch size — the win shrinks as concurrency rises and the GPU shifts from memory-bound to compute-bound.
- Treat vendor multipliers (2x, 15x) as workload- and hardware-specific ceilings, not a number you inherit automatically; validate against your own agent's decode traffic.
- Because the technique is lossless by construction, it is safe to roll out broadly once tuned — there is no accuracy eval cycle to run, only a latency/cost one.

## Failure modes
- **Assuming the speedup is free at any batch size.** At high concurrency, verify compute competes with the batch; the benefit shrinks or vanishes once decode is compute-bound.
- **Mismatched draft and target.** Swapping in an unrelated small model, or reusing a draft head trained against a different target checkpoint, tanks the acceptance rate and can make decode slower than not speculating at all, since you still pay the draft cost with little payoff.
- **Treating headline multipliers as guaranteed.** A hardware-co-designed benchmark number reflects a specific model, batch size, and accelerator; a different production workload will see a different number, often much smaller.
- **Believing it changes output quality.** It is lossless by construction; a quality change after enabling it means a bug in the accept/reject implementation.

## Related
See [speculative decoding](/topic/speculative-decoding) for current vendor and hardware coverage, and [agent latency](/topic/agent-latency) for why the strictly sequential decode loop this technique attacks dominates an agent's wall-clock in the first place.
