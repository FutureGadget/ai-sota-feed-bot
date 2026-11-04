---
slug: agent-eval-design
title: "What should an agent eval actually measure?"
question: "What should an agent eval actually measure?"
summary: "A useful agent eval grades the trajectory as well as the output, matches grader cost to check frequency, repeats runs per configuration, and is audited as hard as the agent: fixing one eval moved a score from 42% to 95%."
status: active
cluster: evaluation
updated: 2026-11-04
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
  - id: arxiv-2610-11678-trace-verifier-brittleness
    kind: benchmark-result
    title: "TRACE: Diagnosing Verifier Brittleness in Agentic Evaluation"
    url: "http://arxiv.org/abs/2610.11678v1"
    sid: "10abc73be739f08b"
    added: 2026-10-09
    note: "Protocol that mutates one part of an eval, compares paired runs, and rescores unchanged trajectories. Renaming tools cut a scripted agent's score by 0.250 with identical operations; restoring names at scoring time closed the gap. On tau2-bench (88 tasks), misleading tool names lowered every agent's reward 0.20-0.44, while identical reruns flipped 15-36% of outcomes. Two frontier judges disagreed on 57% of records."
  - id: arxiv-2609-37315-executable-contract-audit
    kind: benchmark-result
    title: "Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments"
    url: "https://arxiv.org/abs/2609.37315"
    sid: "ec84f4f58551c9cf"
    added: 2026-10-14
    note: "Checks each simulated tool against its advertised interface across 34 mutating tools in four benchmarks and confirms seven tool defects plus one evaluator property. On AgentDojo, at least 5 of 25 mutating tools diverge from their contract. On tau2-bench, the evaluator rewards a refuel of a suspended line and fails the repaired tool. A clinical benchmark's tool reports writes it never made, and its grader counts that message as success."
  - id: agent-eval-design-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-09-02
    note: "A low eval score is a claim about two things at once: the agent's behavior and the eval's own correctness. Builders default to debugging the first without checking the second. Treat the eval as software that needs its own bug-fixing pass before trusting what it reports about the agent."
  - id: episem-bench-2026-missing-evidence
    kind: benchmark-result
    title: "EpiSEM-Bench: Evaluating Safety and Evidence Recovery in LLM Agents under Missing Evidence"
    url: "http://arxiv.org/abs/2610.31650v1"
    sid: "9831d6e2b082e033"
    added: 2026-10-23
    note: "Executable benchmark of 300 matched unsafe/safe task pairs across six domains and ten models. Suppressing a safety-relevant fact from a tool response, while every returned statement stays true, can lead agents to take prohibited actions. Models differ widely in omission robustness and evidence acquisition; giving agents recovery access reduces unsafe execution for all ten. Abstract-level read only; per-model rates not verified."
  - id: arxiv-2611-04399-silent-instrument-errors
    kind: benchmark-result
    title: "Silent Instrument Errors Reorder Agent Leaderboards"
    url: "http://arxiv.org/abs/2611.04399v1"
    sid: "7dfaaa125cb6bf17"
    added: 2026-11-04
    note: "Audits HAL and tau2-bench from published artifacts. A 13-point gap against a specialized scaffold came from the grader: the general agent ended conversations in a way that never triggered grading, so about half its episodes were stored as failures. Regrading closed the gap without rerunning any agent. Also found double-counted cost, grader actions logged as agent actions, and a mode check that cut four files' scores by 59-82 points with no error."
  - id: arxiv-2610-32110-warped-formatters
    kind: benchmark-result
    title: "Who Verifies the Tools? How Warped Formatters Mislead Agents and Their Verifiers"
    url: "http://arxiv.org/abs/2610.32110v1"
    sid: "bd36dcd4473fffd5"
    added: 2026-11-04
    note: "Tool output that omits search limits, result caps, or identifier namespaces misleads agents even when the tool computed correctly. Stating the omitted details cut unsupported claims for three of four failure types. In one test, verifiers moved from accepting 90 of 90 incorrect answers to rejecting 90 of 90. Verifiers caught the errors once given the missing facts. Abstract-level read only."
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
**Start from real failures.** Anthropic recommends 20-50 tasks drawn from cases that went wrong, each with an unambiguous spec and a reference solution; ambiguity produced the 42%-to-95% CORE-Bench jump. Include negative cases where the right behavior is to refuse, or solvable-only suites cannot detect overconfidence.

**Keep the environment stable and grade outcomes.** A flaky sandbox produces noise indistinguishable from a regression. Exact step matching penalizes a correct result reached by a different path, so grade the outcome and, separately, the trajectory.

**Grade the artifact each agent type produces.**

- Coding: unit tests for the outcome, a transcript pass for process.
- Conversational: backend state plus an LLM rubric for tone.
- Research: groundedness, coverage, and source quality as separate checks.
- Computer use: interface and backend state, since a correct-looking screen can hide a failed action.

**Measure the configuration, repeatedly.** In an 18,000-trajectory study, 54% of outcome variance was run-to-run noise within identical configurations, and task information moved results more than time budget or model size. TRACE found identical reruns flip 15-36% of outcomes.

**Test the scorer when a score moves.** TRACE rescored unchanged trajectories after renaming tools: restoring the names erased a 0.250 drop.

**Audit the instrument.** A leaderboard audit traced a 13-point gap to the grader: about half of one agent's episodes never triggered grading and were stored as failures. Regrading closed it without rerunning the agent.

**Make tool output state its limits.** Results printed without their caps or search limits mislead agent and verifier alike; verifiers accepted 90 of 90 wrong answers until the omitted facts were stated.

**Audit the simulated tools.** In four benchmarks, 7 defects appeared across 34 mutating tools; one clinical tool claimed writes it never made, and the grader scored that as success. Repeated runs never expose a defect present every time.

**Watch for saturation.** Near the ceiling, the eval stops separating good from great; see [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap).

## How to apply
- **Audit the eval before touching the agent.** Read failing transcripts by hand for ambiguous specs, wrong references, or a grader that missed a valid path.
- **Start from 20-50 real failures** drawn from production.
- **Report pass@k and pass^k.** One aggregate hides which you have.
- **Match grader type to cadence.** Code-based on every commit; model-based for nuance; humans to calibrate the automated graders.
- **Grade the trajectory as well as the output.**
- **Rescore before you blame the agent.** Rescore unchanged trajectories under the old format; if the gap closes, the scorer moved.
- **Report the graded fraction and pin evaluator versions.** Publish a diff when you regrade.
- **Run each configuration several times and report the spread.**
- **Treat task information, budget, and tooling as eval dimensions.** Test self-verification as a tool, not a prompt line.
- **Check tools against their contract.** Confirm reported state matches written state, and that output states its caps and limits.
- **Retire saturated evals.**

## Failure modes
- **Debugging the wrong thing:** changing the agent without checking the eval for ambiguous specs or grader bugs.
- **One aggregate score:** hiding whether failure is occasional or total.
- **Exact step matching:** penalizing a valid alternate path.
- **No negative cases:** overconfidence goes uncaught.
- **Trusting tool output as ground truth:** a defective or unlabeled tool makes the grader reward actions that never happened.
- **Silent instrument errors:** ungraded episodes counted as failures reorder a leaderboard with no error.
- **Brittle scorers:** a cosmetic change becomes a fake regression.
- **Single-run comparisons:** variance read as a real difference.
- **Misattribution:** crediting the model when tooling also changed.
- **Optimizing a saturated eval.**

## Related
See [agent evaluation](/topic/agent-evaluation), [agent benchmarks](/topic/agent-benchmarks) for where public benchmarks diverge from your own eval, [can you trust an LLM-as-judge score?](/foundations/llm-judge-reliability) for model-based grader failures, and [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap) for reading a score as a production claim.
