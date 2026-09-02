---
slug: agent-eval-design
title: "What should an agent eval actually measure?"
question: "What should an agent eval actually measure?"
summary: "An agent eval only earns its keep if it grades the trajectory (not just the final text), separates cheap deterministic graders from expensive model-based ones, and gets audited as hard as the agent — Anthropic's own eval-building guidance reports a coding benchmark score jumping from 42% to 95% after fixing bugs in the eval itself, not the agent."
status: active
cluster: evaluation
updated: 2026-09-02
audience: "strong-software-engineer"
related_topics: [agent-evaluation, agent-benchmarks]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: anthropic-2026-demystifying-agent-evals
    kind: primary-doc
    title: "Demystifying evals for AI agents"
    url: "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents"
    note: "Anthropic's own guide to building agent evals. Defines an eval as an input plus grading logic, and names three grader types — code-based (fast, cheap, objective), model-based (flexible, handles nuance, non-deterministic and expensive), and human (highest quality, slowest, most expensive). Gives an eight-step program for starting an eval: begin with 20-50 tasks pulled from real failures rather than hundreds of synthetic ones, convert existing manual checks into test cases, write unambiguous tasks with reference solutions, balance positive and negative cases, build stable isolated test environments, prefer deterministic graders over brittle step-by-step checking, read transcripts regularly to verify the grader is being fair, and watch for eval saturation once scores plateau. Introduces pass@k (probability at least one of k attempts succeeds) and pass^k (probability all k attempts succeed) as the two metrics needed once agent behavior is non-deterministic across runs. Gives agent-type-specific grading guidance: coding agents get unit tests plus separate transcript grading; conversational agents combine state verification with LLM rubrics for tone; research agents need groundedness, coverage, and source-quality checks; computer-use agents need both interface-state checks (DOM, screenshots) and backend state checks. Reports that Opus 4.5's measured score on CORE-Bench rose from 42% to 95% after the Anthropic team fixed grading bugs, ambiguous task specifications, and stochastic tasks in the eval itself — the agent's underlying capability had not changed."
  - id: story-6c790a16de0afd2b-demystifying-agent-evals
    kind: story
    sid: "6c790a16de0afd2b"
  - id: agent-eval-design-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "A low eval score is a claim about two things at once — the agent's behavior and the eval's own correctness — and builders default to debugging the first without ever checking the second. Treating the eval itself as a piece of software that needs its own bug-fixing pass, before trusting what it reports about the agent, is the practical takeaway underneath Anthropic's specific grading guidance."
covers_evidence:
  - anthropic-2026-demystifying-agent-evals
  - story-6c790a16de0afd2b-demystifying-agent-evals
  - agent-eval-design-editorial-synthesis
---

## Builder consequence
A low eval score usually gets read as "the agent failed." Anthropic's own eval-building guidance reports a case where that read was wrong: Opus 4.5's score on CORE-Bench rose from 42% to 95% once the team fixed grading bugs, ambiguous task specs, and stochastic tasks in the eval — the agent's capability never changed. Before you spend a cycle improving an agent that scored badly, spend an hour checking whether the eval is the thing that's broken.

## Short answer
An agent eval is an input plus grading logic, and the grading logic is usually the weak link. Three grader types trade off differently — code-based graders are fast, cheap, and objective but brittle; model-based graders handle nuance but are non-deterministic and expensive; human graders are the gold standard but too slow and costly to run continuously. Because agent behavior is non-deterministic across runs, a single pass/fail number understates what you need to know: pass@k (does at least one of k attempts succeed) and pass^k (do all k attempts succeed) answer different production questions — the first about whether the agent can solve the task at all, the second about whether you can trust it to solve the task reliably every time. A score that looks bad by either metric can still mean the eval, not the agent, is where the bug lives.

## Builder model
Think of an eval as software with the same failure surface as any other software: it has bugs, ambiguous specs, and flaky (stochastic) behavior, and those bugs produce exactly the same symptom as a real agent failure — a low score. Two consequences follow:

- **A grader is a build choice with a cost/accuracy trade-off, not a fixed requirement.** Code-based graders (string matching, unit tests, static analysis) are cheap enough to run on every commit but can only check what you thought to encode. Model-based graders catch nuance a static check can't express but introduce their own non-determinism and cost — see [can you trust an LLM-as-judge score?](/foundations/llm-judge-reliability) for how that specific instrument can fail. Human graders set the quality bar but don't scale to continuous use. Most real eval suites mix all three deliberately, matching grader cost to how often and how urgently that check needs to run.
- **A single score hides whether failure is rare or reliable.** pass@k and pass^k answer different questions from the same k attempts. A coding agent that solves a task on 1 of 5 tries (weak pass@5, weak pass^5) is a different risk than one that solves it on 4 of 5 (strong pass@5, weak pass^5) — the second is close to production-ready with a retry loop, the first is not solving the task at all. Reporting only an aggregate accuracy collapses that distinction.

## Mechanism
An eval program starts from real failures, not a from-scratch task list: Anthropic's guidance is to begin with 20-50 tasks pulled from cases the team has actually seen go wrong, not hundreds of synthetic ones, because a synthetic task set can miss the failure mode that matters and inflates the effort of building the eval before it has proven useful. Manual QA checks a team already runs by hand convert directly into automated test cases. Each task needs an unambiguous specification and a reference solution — an ambiguous task is graded inconsistently regardless of how good the grader is, which is exactly the class of bug that produced Anthropic's CORE-Bench jump. The task set should include negative cases (situations where the correct agent behavior is to refuse, defer, or say it doesn't know) alongside positive ones, since an eval built only from tasks the agent should solve can't detect overconfidence.

Test environments need to be stable and isolated — a flaky sandbox or shared external state introduces the same score noise a broken grader would, and it's indistinguishable from a real agent regression without the same debugging pass. Deterministic graders are preferred over brittle step-by-step checking (verifying the agent hit an exact intermediate sequence of actions) because agents often reach a correct outcome through a different, still-valid path; grading the outcome and, separately, the trajectory's overall soundness is more robust than requiring an exact match to one expected sequence.

Grading strategy differs by agent type because the artifact worth checking differs: a coding agent's output has a checkable ground truth (does the code pass the unit tests), so unit tests grade the outcome while a separate pass grades the transcript for process quality (did it take reasonable steps, not just reach a lucky final state). A conversational agent has no single checkable output, so state verification (did the right backend action happen) pairs with an LLM rubric for qualities like tone that only a model-based grader can assess. A research agent's output requires checking groundedness (is the claim actually supported by what was retrieved), coverage (did it miss an obvious source), and source quality — three different checks, not one score. A computer-use agent needs both what the interface shows (DOM state, screenshots) and what actually happened underneath (backend state), because an agent can produce a screen that looks correct while the underlying action failed or vice versa.

Finally, eval saturation is a signal to watch for on its own: once scores plateau near the ceiling, the eval has stopped discriminating between a good and a great agent, and continuing to optimize against it risks tuning to the eval's specific blind spots rather than to real capability — the same dynamic covered in [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap) for benchmarks generally.

## Evidence
- Primary-doc-backed: Anthropic's own eval-engineering guidance lays out the three grader types, the eight-step program for starting an eval, the pass@k/pass^k distinction, and per-agent-type grading guidance, all as practices the team uses to build agent evals internally.
- Primary-doc-backed: the same guidance reports a concrete before/after measurement — Opus 4.5 on CORE-Bench moved from 42% to 95% purely from fixing grading bugs, ambiguous specs, and stochastic tasks in the eval, with no change to the agent — direct evidence that eval quality can dominate the measured score.
- Editorial inference: the practical discipline of auditing the eval before trusting a low score is LLM Digest's synthesis of what Anthropic's guidance implies for how a team should react to a bad result.

## How to apply
- **When an eval score looks bad, audit the eval before you touch the agent.** Read a sample of failing transcripts by hand and check whether the task spec was ambiguous, the reference solution was wrong, or the grader missed a valid alternative path — cheaper than an agent-side fix if the eval is the actual bug.
- **Start an eval from 20-50 real failure cases, not a large synthetic set.** A small set built from cases you've actually seen fail in production catches the failure modes that matter faster than a large but generic task list.
- **Report both pass@k and pass^k when k attempts are available.** They answer different production questions (can it ever solve this vs. can you trust it every time) and collapsing them into one aggregate number hides which one you actually have.
- **Match grader type to how often and how urgently the check needs to run.** Use code-based graders for anything you can express deterministically and want on every commit; reserve model-based graders for qualities (tone, groundedness, nuance) a static check can't express; keep human grading for periodic calibration of the automated graders, not as the primary loop.
- **Grade the trajectory, not only the final output, for agentic tasks.** A coding agent's unit-test pass and its process quality are different signals — a lucky pass through a bad process is a risk the outcome-only score won't show you.
- **Watch for saturation.** If scores plateau near ceiling, stop optimizing against that eval version and either raise its difficulty or treat further gains on it with skepticism.

## Failure modes
- Debugging the agent when the eval is broken: chasing a low score by changing the agent without first checking the eval for ambiguous specs, wrong reference solutions, or grader bugs — Anthropic's own 42%-to-95% jump came entirely from the second kind of fix.
- Reporting a single aggregate score for non-deterministic agent behavior, hiding whether failure is common-but-rare-to-repeat (bad pass^k, decent pass@k) or genuinely can't-solve-it (bad on both).
- Requiring an exact intermediate-step match instead of grading trajectory soundness and outcome separately, penalizing an agent that reached a correct result through a different valid path.
- Building an eval only from tasks the agent should succeed at, with no negative cases, so overconfident or unwarranted-refusal behavior never gets caught.
- Running evals against a flaky or shared test environment, introducing score noise indistinguishable from a real regression.
- Continuing to optimize against a saturated eval, tuning to that eval's specific blind spots instead of real capability.

## Related
See [agent evaluation](/topic/agent-evaluation) for the broader problem of grading agent trajectories, [agent benchmarks](/topic/agent-benchmarks) for how fixed public benchmarks are built and where they diverge from a team's own eval, [can you trust an LLM-as-judge score?](/foundations/llm-judge-reliability) for the specific failure modes of the model-based grader type this concept only summarizes, and [does a high benchmark score predict production reliability?](/foundations/benchmark-production-reliability-gap) for what happens once an eval's score, even a correct one, gets read as a claim about production behavior.
