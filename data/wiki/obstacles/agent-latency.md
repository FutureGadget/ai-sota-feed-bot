---
slug: agent-latency
kind: obstacle
title: "Agent loops multiply per-call latency into slow, expensive runs"
area: latency
status: active
solutions: [speculative-decoding, context-compaction]
obstacles: []
related_storylines: []
evidence: [0ca61ed96ddd38e5, e313a171aa375adf, 537f21de13e2a85a, c66b542cadbb4592, 6cc910fb018354bf, e2f43565cf7c0d8e, dca39fe0489bebd0, 0933879c19d86a9c, bbc9b11398e5a4c1, c0c3ec4a6aba7980, d3e345ae085932a6, 7b0c24a5e0c92a10, c841afae435d6473, 07f37058d3d7c72b, 3ce97f6a8c6c0f29, 76c7b104c7dfd8b4, d08095949d6300c2, 3f7129b93f7a9b75, 66c593bb8d830d85, 94813f8b6bc86093, 90414bf337cae373, 73489cffeb776e1f, 309c04c4364dddf7, b811cc97eff4aae9, aba45d95421e53e0, 5ed10ede4abacd52, 64c163bb191bab4e, deec56a13e2b9b57]
updated: 2026-08-04
covers_evidence: [0ca61ed96ddd38e5, e313a171aa375adf, 537f21de13e2a85a, c66b542cadbb4592, 6cc910fb018354bf, e2f43565cf7c0d8e, dca39fe0489bebd0, 0933879c19d86a9c, bbc9b11398e5a4c1, c0c3ec4a6aba7980, d3e345ae085932a6, 7b0c24a5e0c92a10, c841afae435d6473, 07f37058d3d7c72b, 3ce97f6a8c6c0f29, 76c7b104c7dfd8b4, d08095949d6300c2, 3f7129b93f7a9b75, 66c593bb8d830d85, 94813f8b6bc86093, 90414bf337cae373, 73489cffeb776e1f, 309c04c4364dddf7, b811cc97eff4aae9, aba45d95421e53e0, 5ed10ede4abacd52, 64c163bb191bab4e, deec56a13e2b9b57]
---

## TL;DR
A chatbot waits on one model call; an agent waits on *many*, in sequence —
plan, call a tool, read the result, decide again — so the wall-clock a user
feels is the per-token decode latency multiplied by the loop length, and a
serving stack tuned for single-shot throughput can still leave an agent feeling
slow. Latency is the run-time twin of [cost](/topic/agent-cost): the same loop
that runs up the bill also runs out the clock.

## State of the art
Latency for agents is being attacked at the **serving layer** and the
**workload-shape layer** at once. The serving engines that host agent traffic
are competing hard on decode latency and throughput — vLLM has moved fastest,
with v0.25.0 deleting the legacy PagedAttention implementation outright now
that Model Runner V2 (MRv2) is the default execution path for every dense
model, and unifying tool-call/reasoning-token parsing across model families
under one Streaming Parser Engine — while Modular's 26.4 ships
state-of-the-art MoE serving, and infra partnerships (NVIDIA + AWS) are pitched
explicitly on "low-latency inference at scale" — but raw engine speed only moves
one term in the agent's latency budget. That serving-layer work is
increasingly hardware- and model-specific rather than generic: vLLM's
integration with Tencent's HPC-Ops backend adds Hopper-optimized attention
and FP8 MoE kernels tuned for the Hunyuan Hy3 model on NVIDIA H20, cutting
time-to-first-token and per-output-token latency on the mixed-length,
bursty decode pattern agent loops actually produce, rather than the uniform
batches a generic benchmark assumes. The newer recognition is that **agent
workloads do not look like chat**: coding agents issue bursty, long-context,
tool-interleaved requests, and characterizing that shape is now its own research
target (TraceLab profiles real coding-agent workloads for LLM serving so the
server can be tuned to them rather than to a generic chat trace). That work is
surfacing agent-specific bottlenecks the chat era never hit — DualPath finds the
binding constraint in agentic inference is **storage bandwidth**, not compute,
because the agent's growing KV/context state has to be streamed back each step —
and one direct answer is shrinking that state: RaBitQCache uses randomized
rotated binary quantization to compress the KV cache and an adaptive top-p token
budget instead of a fixed top-k, cutting the memory-I/O DualPath identifies as the
bottleneck while holding generation quality. A second answer targets the same
bottleneck from the storage side rather than the compute side: OpenLake offloads
KV state from GPU memory into a shared RAM/NVMe tier with a CUDA kernel that
losslessly compresses blocks before they leave the GPU, so a prefix cached on one
host is cheap to fetch from another instead of forcing a fresh GPU to redo the
work — on a 128K-context workload it cut time-to-first-token from 44 seconds to
0.6 seconds when the prefix was reused across hosts. The dev-loop side of latency counts
too: local CI (running checks on the developer's machine instead of round-tripping
to a remote runner) cuts the feedback loop for both human developers and coding
agents, since round-trip time to a CI runner is on the same wall-clock budget as
each model call.
The other lever is the model itself: latency-first small models (Kog's Laneformer
2B, built for its inference engine) trade frontier breadth for predictable speed
on the bulk of an agent's calls, the same downshift logic that drives cost.
Latency also has a hard product floor in interactive modes — a voice agent that
pauses too long gets hung up on, which is why low-latency voice stacks (Loka on
Amazon Nova 2 Sonic) treat round-trip time as a first-class design constraint,
not a tuning afterthought.

**Query volume compounds the same way tool calls do**: a single agent
request that fans out into tens of database or API queries, and a
multi-step workflow into hundreds, inherits chat-era latency expectations
("a few hundred milliseconds feels responsive, a couple of seconds feels
broken") for every one of those queries, not just the top-level turn — so a
semantic-layer pattern built for dashboards (pre-aggregated rollups serving
many queries through query rewriting, columnar storage with partition
pruning) is being repurposed as agent infrastructure precisely because it
was already built for many small, interactive queries instead of a few large
batch ones. **New models get latency-tuned serving on day one, not
retrofitted later**: vLLM shipped full-feature-parity support for Thinking
Machines' 1T-parameter Inkling model the day it released, reaching 380
tokens/sec/user with speculative decoding versus 140 without on 4 GB200
GPUs — folding a brand-new architecture into the same speculative-decoding
and disaggregation levers already on this page instead of waiting for a
follow-up optimization pass.

**Batching** is the other lever a bursty agent workload stresses directly:
static batching policies need manual tuning per traffic shape and cannot
adapt when request patterns shift mid-run, so adaptive inference batching
that learns a batching policy with reinforcement learning targets exactly the
bursty, heterogeneous load agent tool-calling produces instead of assuming
the steady arrival rate a chat workload has.

The serving layer itself is starting to absorb **agentic behavior**: vLLM's
Semantic Router turns its `vllm-sr/auto` routing feature into a bounded
"micro-agent" runtime — confidence scoring, ratings, and workflow fusion happen
*inside* the serving layer rather than in a separate orchestration hop above
it, collapsing a round-trip that would otherwise cost a full extra model call
and its latency.

**Disaggregation is going one step further than prefill/decode splitting**:
vLLM's TileRT integration plugs a decode-only runtime into vLLM's existing
prefill/decode split, transferring KV state from stock-vLLM prefill nodes to
specialized decode nodes over RDMA and running multi-token speculative
decoding immediately after that state lands — reaching peak decode
throughput at a best-case 4.0-token speculative-acceptance rate on an
8-GPU setup, though today it's limited to one in-flight request per decode
node and a narrow model list. It's a further specialization of the same
disaggregation trend already on this page, pushing decode itself onto
purpose-tuned hardware/software rather than just splitting prefill from
decode.

**Disaggregation is also splitting along a second axis — compute type, not
just pipeline phase**: vLLM's AFD (Attention-FFN Disaggregation) plugin
separates attention and FFN computation onto different execution paths for
MoE model serving, with GPU and Ascend NPU backend support, connector-based
execution, and graph and micro-batching ("ubatching") support. Where the
prefill/decode split above divides a request by *phase*, AFD divides a
single forward pass by *compute type*, giving operators a second knob for
allocating hardware across the attention and FFN paths of the large open MoE
models now shipping in volume.

**Scheduling** is getting an agent-specific rework, not just faster kernels:
SMetric finds agent traffic already has high KV-cache reuse (>80% in
production) but generic schedulers over-index on cache locality and let
load imbalance cap cluster throughput, so it splits requests into a
load-balanced first hop per agent session and a cache-aware routing decision
for every request after — reporting 10-16% throughput gains under
prefill-decode colocation and 2-34% prefill gains under disaggregated
serving versus prior schedulers, without giving up the cache-reuse win a
purely cache-aware scheduler chases. On the engine side, vLLM's transformers
backend uses `torch.fx` graph analysis plus AST rewriting to fuse operations
into optimized vLLM kernels automatically, matching native per-model
integration throughput on dense and MoE Qwen3 models without hand-written
per-model code — cutting the engineering cost of *keeping up* with new model
architectures, which is itself a latency-relevant maintenance tax.

**Day-0 support is extending to hardware, not just models**: vLLM now runs
end-to-end on pre-release NVIDIA Vera Rubin hardware, and separately shipped
a production-scale preview of Kimi K3 support — KDA-aware prefix caching,
fused kernels, optimized MXFP4 MoE, multimodal integration, and initial
NVIDIA and AMD paths — extending the "new models get latency-tuned serving
on day one" pattern already on this page (the 1T-parameter Inkling launch)
to a new GPU generation and a new open-weight architecture at once. Release
v0.26.0 folds a new model family into the same day-0 pattern from the start:
the Inkling family ships with piecewise CUDA graph support, Hopper FA4
relative attention, MTP=1 speculative decoding, LoRA, and NVFP4 quantization
all in one release, alongside a DeepSeek-V4 performance push (a specialized
routing kernel, fused top-k bias, and redundant-copy removal) that shaves
E2E decode latency without touching the serving architecture — the routine,
compounding kind of engine-side gain that adds up across every agent loop
step on that model.

The preview-to-production pattern this page already tracks (day-0 support
landing ahead of a full optimization pass) gets a concrete follow-through:
vLLM's production-scale Kimi K3 preview became efficient day-0 serving
support in the same release cycle, keeping the hybrid KDA prefix caching,
speculative decoding, and disaggregation from the preview while adding
optimized kernels across both NVIDIA and AMD GPUs — evidence the "new
open-weight model, latency-tuned serving on day one" pattern holds across a
model's preview-to-GA transition, not just its initial launch. Vendors
outside the model labs are running the same in-house serving playbook this
page already tracks: Netflix's own LLM-serving platform pairs Triton and
vLLM, a practitioner data point that the serving-layer techniques here
(disaggregation, batching, kernel fusion) are standard operating practice
at large deployers, not just a model lab's launch-day flex. The
serving-layer-absorbs-agentic-behavior thread also gains a name for what
comes after routing: vLLM's Semantic Router frames its next phase as
building the training, evaluation, and inference engine for a
**Mixture-of-Models** era — treating "which model handles this request" as
a first-class serving-layer decision with its own eval loop, not a one-off
routing feature bolted onto an existing engine.

OpenAI's own account of building GPT-Live — a turnless (no push-to-talk
turn-taking) speech system with a continuous, low-latency voice
architecture — sharpens this page's standing "interactive modes set a hard
latency floor" argument with a concrete engineering case study of hitting
that floor in six months, from the model provider's own product side rather
than a serving-stack vendor's benchmark.

## What's new
OpenAI detailed building GPT-Live, a turnless, continuous-voice speech
system, in six months — a concrete engineering account of meeting the
low-latency floor voice interaction demands, from the model provider's own
product side rather than a serving-stack benchmark.

vLLM's Kimi K3 support moved from production-scale preview to efficient
day-0 serving in the same release cycle, keeping the preview's KDA prefix
caching, speculative decoding, and disaggregation while adding optimized
NVIDIA and AMD kernels — the "day-0 latency-tuned serving" pattern already
on this page holding across a model's preview-to-GA transition. Separately,
Netflix detailed its own in-house Triton+vLLM serving platform, and vLLM's
Semantic Router named its next phase "Mixture-of-Models," treating model
routing as a first-class serving-layer discipline with its own training and
eval loop rather than a bolted-on routing feature.

## Why it matters for platform engineers
Latency is where the agent's architecture meets the user's patience and the
GPU's bill — the three trade against each other directly. The job is to budget
latency across the *whole loop*, not per call: count the sequential model hops,
push what you can to a faster or smaller model, cut the tokens that have to be
decoded and streamed each step (compaction, KV reuse), and pick a serving engine
tuned to the bursty, long-context shape agents actually produce rather than to a
chat benchmark. Interactive modes (voice, live coding) set a hard ceiling, so the
deliverable is a latency budget you can reason about per task, not a one-time
inference optimization.
