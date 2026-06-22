# Agent Engineering Experiment Series

## Problem Statement

How might we help engineers building agents and agent platforms make better
choices about skills, harnesses, and models through reproducible experiments,
without turning llm-digest.com into a generic review site or beginner learning
publication?

## Recommended Direction

Build an ongoing **Agent Engineering Experiment Series** around evidence that is
usually missing from product announcements and ordinary reviews: what the agent
actually did. Each edition should expose the task, environment, versions,
instructions, repeated runs, observed trajectories, evaluation method, cost,
and limitations.

Start with **Agent Skill Lab**. Compare a complete community skill against both
no-skill and minimal-instruction baselines, then explain how planning, tool use,
recovery, unnecessary work, and final task quality changed. This is relatively
cheap to test, closely aligned with agent builders, and differentiated from
prompt collections because it studies behavior rather than reproducing prompt
text.

Add **Harness Field Tests** after the methodology is credible. These should
answer job-specific purchasing questions—such as whether a harness can run
scheduled work remotely or recover from an interrupted repository task—rather
than produce a universal ranking. Add **Benchmark Decoder** later as supporting
reference material that helps readers interpret evidence used in the
experiments. Keep broad zero-to-hero LLM education on the owner's personal blog.

The series is both an editorial format and a growth loop: each experiment is a
durable reference, a reason to return for the next result, and a concrete
subscription proposition.

## Key Assumptions to Validate

- [ ] Readers value trajectory evidence more than ordinary feature reviews —
      compare artifact engagement and return visits against existing editorial
      pages.
- [ ] A recurring experiment creates subscription intent — track subscriptions
      attributable to experiment pages and calls to action.
- [ ] Three repeated conditions reveal stable behavioral differences at an
      affordable cost — pilot one task and measure variance, tokens, latency,
      and total execution expense.
- [ ] Findings remain useful despite rapid product changes — add visible version
      metadata and measure whether a documented expiry/retest policy is
      operationally sustainable.
- [ ] The experiment can separate skill effects from model and harness effects —
      hold the environment constant first, then document remaining sources of
      variance.

## MVP Scope

Publish three Agent Skill Lab editions using one shared experiment contract:

- one fixed engineering task per edition;
- no skill, minimal instruction, and complete skill conditions;
- multiple runs per condition;
- pinned model, harness, permissions, repository fixture, and budget;
- task success, trajectory, tool usage, recovery, unnecessary work, tokens,
  latency, and cost;
- representative artifacts plus a concise practical recommendation;
- analytics for page completion, return visits, artifact clicks, and
  subscriptions.

The MVP succeeds if it establishes a repeatable methodology and produces a
measurable readership or subscription signal. It does not need to establish a
statistically universal ranking.

## Not Doing (and Why)

- **Universal rankings or “best agent” claims** — workflow fit is contextual,
  and a narrow experiment cannot support a universal conclusion.
- **Every model × harness × skill combination** — combinatorial cost would
  prevent a consistent publishing cadence before demand is proven.
- **Automated public leaderboards** — they encourage score optimization before
  the evaluation methodology is trustworthy.
- **Feature matrices without hands-on verification** — vendor descriptions do
  not answer whether a workflow succeeds in practice.
- **Beginner-oriented LLM education** — it weakens the site's practical focus
  on engineers already building and operating AI systems.
- **Model leaderboard aggregation** — existing sites already provide scores;
  the differentiated job is explaining what evidence means for engineering.

## Open Questions

- Which skill and engineering task create the strongest first demonstration?
- How many runs per condition are enough to expose meaningful trajectory
  differences without making each edition too expensive?
- Which trajectory artifacts can be published without leaking secrets,
  copyrighted repository content, or hidden model reasoning?
- Should experiments live under a dedicated site section immediately, or begin
  as Playbook-linked editions until retention is demonstrated?
- What event and attribution model will connect experiment readership to return
  visits and subscriptions?
