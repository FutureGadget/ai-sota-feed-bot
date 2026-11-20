---
slug: llm-judge-reliability
title: "Can you trust an LLM-as-judge score?"
question: "Can you trust an LLM-as-judge score?"
summary: "An LLM judge is a measurement instrument with its own biases, not ground truth — validate it the same way you validate the agent it grades, and for agent trajectories with checkable evidence, consider a deterministic scorer instead."
status: active
cluster: evaluation
updated: 2026-11-20
audience: "strong-software-engineer"
related_topics: [agent-evaluation, llm-as-judge]
related_playbook_cards: [pb-audit-llm-judges-for-position-and-language-bias]
related_storylines: []
evidence:
  - id: babeljudge-2026-judge-bias
    kind: benchmark-result
    title: "BabelJudge: Measuring LLM-as-a-Judge Reliability Across Languages and Agent Trajectories"
    url: "http://arxiv.org/abs/2606.22329v1"
    added: 2026-06-28
    note: "Builds gold-labeled pairs by perturbing known-good answers (no human annotation) and measures position bias, verbosity bias, order inconsistency, and cross-lingual degradation in a Qwen2.5-7B-Instruct judge. Raw accuracy (0.835 Hindi vs. 0.660 Swahili) understates the gap: bias-penalized reliability falls from 0.714 to 0.550, and order consistency collapses to 0.480 under slot swaps, near random. One judge model tested."
  - id: encoder-decoder-safety-judges-2026
    kind: benchmark-result
    title: "Do Encoders Suffice? A Systematic Comparison of Encoder and Decoder Safety Judges for LLM Adversarial Evaluation"
    url: "http://arxiv.org/abs/2606.25782v1"
    added: 2026-06-28
    note: "Benchmarks fine-tuned encoder classifiers against LLM-based judges for detecting harmful outputs across several attack techniques, testing whether a much cheaper, lower-latency judge architecture can substitute for an LLM judge without a major accuracy loss. Safety-classification setting only; no headline figure is recorded here."
  - id: langchain-fireworks-trace-judge-2026
    kind: production-field-report
    title: "Building a 100x Cheaper Trace Judge with Fireworks"
    url: "https://www.langchain.com/blog/building-a-100x-cheaper-trace-judge-with-fireworks"
    added: 2026-06-28
    note: "LangChain and Fireworks fine-tuned a small open model on production trace labels and matched frontier-judge performance at roughly 1/100th the cost. Vendor-reported, on their own narrow trace-grading task. Shows a judge's behavior can be distilled and re-validated rather than locked to whichever frontier model wrote the first version."
  - id: linear-sales-email-eval-miss-2026
    kind: production-field-report
    title: "Why most AI evals would miss the Linear sales email failure"
    url: "https://tenureai.dev/writing/why-most-ai-evals-would-miss-the-linear-sales-email-failure"
    added: 2026-06-28
    note: "Practitioner postmortem on a real production failure that a typical eval suite and judge would have scored as a pass. Single incident, no rates; shows judge accuracy on a benchmark does not guarantee the judge catches the failure that actually matters."
  - id: groundeval-2026-judge-free-agent-evaluation
    kind: benchmark-result
    title: "GroundEval: A Deterministic Replacement for LLM-as-Judge in Stateful Agent Evaluation"
    url: "https://arxiv.org/abs/2606.22737"
    added: 2026-07-10
    note: "In a case study, two frontier LLM judges scored a plausible agent response 0.85 or higher while the recorded trajectory showed the agent never retrieved the artifact its answer depended on; GroundEval scored it 0.000. Replaces the judge with a deterministic scorer over grounded, time-bounded, access-controlled evidence on three tracks: Silence, Perspective, and Counterfactual. The authors' case studies suggest the failure is common, not exceptional."
  - id: google-cloud-audit-llm-evaluators-2026
    kind: primary-doc
    title: "Who judges the judge? Three helpful ways to audit your LLM evaluators"
    url: "https://cloud.google.com/blog/topics/consulting/three-ways-to-audit-your-llm-evaluators"
    sid: "4e6e796fa0c5bfc0"
    added: 2026-10-21
    note: "Google Cloud's audit recipe: measure score variance across repeated passes on identical inputs, compare against human experts with chance-corrected metrics, and use at least two judge models on decomposed criteria, flagging divergence. Cites prior work that swapping option order can flip a verdict over 75% of the time. Gives no thresholds or pass counts."
  - id: hamel-decision-model-evals-2026
    kind: production-field-report
    title: "How To Use Decision Models for Evals"
    url: "https://hamel.dev/blog/posts/decision-model-evals"
    sid: "58b479d20c57cce8"
    added: 2026-10-21
    note: "Tests six small decision models on 98 apartment-leasing agent traces (61 failures) with five-fold cross-validation. Tuning the default 0.50 threshold recovers performance; the cheapest model scored F1 0.79 at 0.82 cents per 100 runs versus 0.87 at 3.72 cents. Calibration must be measured: one group predicted 8% failure but 60% failed. Small, single dataset."
  - id: scale-reversal-judge-bias-2026
    kind: benchmark-result
    title: "Rubric Semantics or Numerical Priors? Auditing Scale-Direction Bias in LLM Judges"
    url: "http://arxiv.org/abs/2611.25588v1"
    sid: "d59766235f01efbf"
    added: 2026-11-20
    note: "Inverts a rubric's score anchors (1 = best instead of 5 = best) without changing the criteria and checks whether judges give consistent scores. Across five meta-evaluation benchmarks and seven open and proprietary judges, violations are widespread, and raw reversal agreement is misleading until normalized against each judge's own run-to-run noise. Averaging scores over both anchor directions reduces the dependence without hurting agreement with human ratings."
  - id: verification-transport-2026
    kind: benchmark-result
    title: "Do Verifier Judgments Survive Abstraction? Measuring Verification Transport for LLM Agent Evaluation"
    url: "http://arxiv.org/abs/2611.18471v1"
    sid: "a44ee00fea440f11"
    added: 2026-11-20
    note: "Shows the same frozen agent execution, viewed through composed tools, delegation, or a compacted history, changes verifier verdicts. Across four benchmarks, seven verifier backbones, four protocols, and three boundaries, judgment failure reaches about 31% under macro abstraction plus delegation. Direct verification flips to wrong verdicts; evidence-grounded protocols abstain instead. Restoring execution provenance recovers 85.5% of failures."
  - id: agentdojo-verdict-audit-2026
    kind: benchmark-result
    title: "Did the Attack Really Work? Auditing, Re-running, and Sealing AI-Agent Security Findings with .sova"
    url: "https://zenodo.org/records/24321025"
    sid: "cd759e6684ea23fc"
    added: 2026-11-20
    note: "Audits AgentDojo's automated attack-success checks against the tool calls agents actually made. Agreement is 97.7% on 19,381 runs, but the checker scored 433 runs as no attack where the agent paid the attacker or took the decisive action: 11.9% of real attacks. A reply-text check also counted warnings as attacks. Preprint, not peer reviewed; the author's company builds the audit tool."
  - id: llm-judge-reliability-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-06-28
    note: "For agent builders, an LLM-as-judge score is an output of a measurement instrument with its own bias profile, not a ground-truth label, so the judge needs the same validation discipline as the agent it grades."
---

## Builder consequence
If you grade agent traces with an LLM judge, the score is not a fact about the agent. It is the agent filtered through a second model with its own failure modes. Before wiring a judge into CI gating or a dashboard, find out whether it favors a slot, a length, a language, or a rubric's number direction, and whether it still agrees when it sees a compacted or delegated view of the same run.

## Short answer
LLM-as-judge accuracy on a held-out set is necessary but not sufficient. Judges carry systematic biases toward position, length, language, and score-anchor direction that raw accuracy hides. A judge that passes a benchmark can still miss the failure the eval exists to catch.

Two deeper gaps sit underneath. A judge grades the answer's plausibility, not whether the trajectory earned it. Its verdict also depends on which view of the trajectory it reads: Verification Transport measured about 31% judgment failure once execution crossed delegation and tool-composition boundaries. Treat the judge as a component under test, give it the provenance, and where evidence is checkable, use a deterministic scorer that you audit too.

## Builder model
A judge is a classifier with a prompt instead of a training loop, and classifiers fail in ways one aggregate accuracy number doesn't show. Judge designs sit on a spectrum:

- **Prompted frontier LLM:** flexible, expensive, subtly biased.
- **Small fine-tuned classifier** (encoder or distilled LLM) trained on production labels: cheap, fast, narrower, only as good as its labels.
- **Deterministic check** over the recorded trajectory: exact where evidence is checkable, blind to anything its rule didn't anticipate.

All three need what an agent needs: a held-out test set built from real failures, not the cases the scorer was tuned on.

## Mechanism
An LLM judge produces a verdict conditioned on the response, a rubric, and often a second response to compare. Because the verdict is a model output, it inherits model-level artifacts:

- **Position bias:** preferring whichever candidate is shown first. BabelJudge's order consistency fell to 0.480 in Swahili, near random.
- **Verbosity bias:** preferring longer text as a proxy for thoroughness.
- **Distribution-shift degradation:** losing calibration outside its tuned language or domain.
- **Anchor-direction bias:** scoring by numeric priors ("5 is good") rather than the rubric's words, so inverting the scale changes verdicts.

Agent trajectories add a representation problem. In production, one execution reaches the judge as raw tool calls, a composed macro-tool, a sub-agent summary, or a compacted history. Each view hides different evidence, so the same run can get different verdicts. Direct verification tends to flip to a wrong verdict; evidence-grounded protocols tend to abstain, which looks like lower failure but is not more reliable. Restoring provenance recovered most of the failures.

Deterministic trajectory scoring removes the judge where evidence is checkable. GroundEval grades the recorded trajectory against ground truth the system knows: did the agent check before claiming absence (**Silence**), reason only from evidence available at the time (**Perspective**), and use the real causal mechanism (**Counterfactual**)? That catches a fluent, ungrounded answer a final-text judge cannot.

Deterministic checks have their own blind spot: a rule that reads the wrong field misses real outcomes. AgentDojo's attack checker missed 11.9% of runs where the agent executed the attacker's action.

## How to apply
Before trusting a judge's verdicts, run these checks:

- **Order-swap test.** Run every pairwise comparison both ways; count only verdicts that agree.
- **Scale-reversal probe.** Re-score a sample with inverted anchors; if verdicts move beyond the judge's own rerun noise, average both directions in production.
- **Verbosity and per-slice checks.** Track length against verdict; report reliability per language or domain, not pooled.
- **Held-out set from real failures.** Use production failures your team has seen, not cases the judge obviously gets right.
- **Stability and human agreement.** Re-score identical inputs several times; compare against human labels with a chance-corrected metric.
- **Judge the production view, with provenance.** Score the trajectory representation the verifier will see after delegation or compaction, and attach the raw tool-call log it was derived from.
- **Re-validate any cheaper judge.** Test encoders, distilled models, or decision models on the same set; tune thresholds, measure calibration, re-run on every model, prompt, or rubric change.
- **Prefer deterministic scorers, then audit them.** Where evidence is checkable, grade the trajectory against ground truth, and periodically diff the checker's verdicts against the actions actually taken.

## Failure modes
- **Aggregate accuracy worship:** a pooled number hiding a collapse in one slice.
- **Order or anchor blindness:** never testing whether a verdict flips when slots swap or the scale inverts.
- **Benchmark-only validation:** the judge never sees the production failure the eval exists to catch.
- **Set-and-forget judges:** no re-validation after the agent, prompt, or judge model changes.
- **Abstraction blindness:** validating on raw traces, then judging compacted or delegated summaries.
- **Abstention mistaken for accuracy:** a protocol that refuses to rule looks reliable but grades nothing.
- **Grading the answer, not the path:** trusting a fluent answer without checking the trajectory's evidence.
- **Trusting the checker:** treating an automated benchmark verdict as proof without auditing it against actions.

## Related
See [agent evaluation](/topic/agent-evaluation) for grading agent trajectories, [LLM-as-judge](/topic/llm-as-judge) for the model-graded pattern this page interrogates, and [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap) for whether the benchmark itself predicts real-world behavior.
