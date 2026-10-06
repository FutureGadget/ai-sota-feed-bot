---
slug: agent-eval-design
title: "What should an agent eval actually measure?"
question: "What should an agent eval actually measure?"
summary: "A useful agent eval grades the trajectory as well as the output, matches grader cost to check frequency, repeats runs per configuration, and is audited as hard as the agent: fixing one eval moved a score from 42% to 95%."
status: active
cluster: evaluation
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [agent-evaluation, agent-benchmarks]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: anthropic-2026-demystifying-agent-evals
    kind: primary-doc
    title: "Demystifying evals for AI agents"
    url: "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents"
    sid: "6c790a16de0afd2b"
    added: 2026-09-02
    note: "Anthropic's guide to building agent evals. Names three grader types: code-based (fast, cheap, objective), model-based (flexible, non-deterministic, expensive), and human (best quality, slowest). Recommends starting from 20-50 real-failure tasks with unambiguous specs and reference solutions, positive and negative cases, isolated environments, and outcome grading over step matching. Defines pass@k and pass^k. Reports Opus 4.5's CORE-Bench score rising from 42% to 95% after fixing grading bugs, ambiguous specs, and stochastic tasks in the eval."
  - id: arxiv-2610-01618-agents-are-systems
    kind: benchmark-result
    title: "Agents Are Systems, Not Models: Rethinking Agentic Evaluation"
    url: "http://arxiv.org/abs/2610.01618v1"
    sid: "068e3817b6d56fbd"
    added: 2026-10-02
    note: "Runs a coding agent on four scientific tasks that require operating specialist models, across more than 18,000 trajectories varying task information, reasoning approach, self-verification, time budget, and backbone model. 54% of outcome variance came from run-to-run variability within identical configurations. Task information had the largest effect, above time budget or model size; extra time helped only with enough information or a capable model. Verification tools changed behavior substantially; verification prompts had minimal effect."
  - id: agent-eval-design-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-09-02
    note: "A low eval score is a claim about two things at once: the agent's behavior and the eval's own correctness. Builders default to debugging the first without checking the second. Treat the eval as software that needs its own bug-fixing pass before trusting what it reports about the agent."
---

## Builder consequence
A low eval score usually gets read as "the agent failed." Anthropic reports a case where that read was wrong: Opus 4.5's CORE-Bench score rose from 42% to 95% once the team fixed grading bugs, ambiguous task specs, and stochastic tasks in the eval. The agent never changed. Before you spend a cycle improving an agent that scored badly, spend an hour checking whether the eval is what's broken.

## Short answer
An agent eval is an input plus grading logic, and the grading logic is usually the weak link. Three grader types trade cost against accuracy: code-based graders are cheap and objective but only check what you encoded; model-based graders handle nuance but are non-deterministic and expensive; human graders set the bar but don't scale.

Because agents vary run to run, one pass/fail number isn't enough. **pass@k** asks whether the agent can solve the task at all; **pass^k** asks whether it solves it every time. And a bad score on either can mean the eval, not the agent, is broken.

## Builder model
Treat an eval as software with the usual failure surface: bugs, ambiguous specs, and flaky behavior. All three produce the same symptom as a real agent failure — a low score.

- **Grader choice is a cost/accuracy trade-off.** Code-based graders (unit tests, string checks, static analysis) can run on every commit but only check what you encoded. Model-based graders catch nuance but add their own non-determinism; see [can you trust an LLM-as-judge score?](/foundations/llm-judge-reliability). Human graders calibrate the others. Real suites mix all three, matched to how often each check must run.
- **One score hides whether failure is rare or reliable.** An agent that solves a task 1 of 5 times and one that solves it 4 of 5 times both fail pass^5. The second is near production-ready behind a retry; the first is not solving the task.
- **The unit under test is the system.** Task information, tools, budget, and model all move the score, so a result describes the configuration, not the model alone.

## Mechanism
**Start from real failures.** Anthropic recommends 20-50 tasks drawn from cases that actually went wrong, not hundreds of synthetic ones; manual QA checks convert directly into test cases. Each task needs an unambiguous spec and a reference solution, because an ambiguous task is graded inconsistently however good the grader is. That bug class produced the 42%-to-95% CORE-Bench jump. Include negative cases where the right behavior is to refuse, defer, or say it doesn't know; a suite of only solvable tasks cannot detect overconfidence.

**Keep the environment stable and grade outcomes.** A flaky sandbox or shared external state produces score noise indistinguishable from a regression. Exact step-sequence matching penalizes agents that reach a correct result by a different valid path, so grade the outcome and, separately, the soundness of the trajectory.

**Grade the artifact each agent type produces.**

- Coding: unit tests for the outcome, a transcript pass for process.
- Conversational: backend state verification plus an LLM rubric for tone.
- Research: groundedness, coverage, and source quality as separate checks.
- Computer use: interface state (DOM, screenshots) and backend state, since a correct-looking screen can hide a failed action.

**Measure the configuration, repeatedly.** In an 18,000-trajectory study of coding agents, 54% of outcome variance was run-to-run noise within identical configurations, and task information moved results more than time budget or model size. A verification tool changed behavior where a verification prompt barely did. One run per configuration cannot separate an improvement from luck.

**Watch for saturation.** Once scores plateau near the ceiling, the eval stops separating good from great, and further optimization tunes to its blind spots — the dynamic covered in [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap).

## How to apply
- **Audit the eval before touching the agent.** When a score looks bad, read failing transcripts by hand and check for ambiguous specs, wrong reference solutions, or a grader that missed a valid path.
- **Start from 20-50 real failures.** A small set from production catches the failures that matter faster than a large synthetic one.
- **Report pass@k and pass^k.** They answer "can it ever solve this" and "can I trust it every time"; one aggregate hides which you have.
- **Match grader type to cadence.** Code-based graders for anything deterministic, on every commit; model-based graders for tone, groundedness, and nuance; humans for periodic calibration of the automated graders.
- **Grade the trajectory as well as the output.** A lucky pass through a bad process is a risk the outcome score won't show.
- **Run each configuration several times and report the spread.** At 54% run-to-run variance, a single run is mostly noise.
- **Change behavior with tools, not prompt lines.** Treat task information, budget, and tooling as explicit eval dimensions, and test self-verification as a tool or dedicated component.
- **Retire saturated evals.** At ceiling, raise the difficulty or discount further gains.

## Failure modes
- **Debugging the wrong thing:** changing the agent to chase a low score without checking the eval for ambiguous specs, wrong references, or grader bugs.
- **One aggregate score:** hiding whether failure is occasional (decent pass@k, bad pass^k) or total.
- **Exact step matching:** penalizing a correct result reached by a different valid path.
- **No negative cases:** overconfidence and unwarranted refusals never get caught.
- **Flaky environments:** sandbox noise read as an agent regression.
- **Single-run comparisons:** run-to-run variance read as a real difference.
- **Misattribution:** crediting the model for a change when task information, budget, or tooling also changed.
- **Optimizing a saturated eval:** tuning to its blind spots instead of real capability.

## Related
See [agent evaluation](/topic/agent-evaluation), [agent benchmarks](/topic/agent-benchmarks) for where public benchmarks diverge from your own eval, [can you trust an LLM-as-judge score?](/foundations/llm-judge-reliability) for model-based grader failures, and [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap) for reading a score as a production claim.
