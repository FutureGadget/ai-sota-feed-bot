---
title: "Paired protocol isolates upstream messages: real delivery raised risky violations to 21.4% from 1.0% hidden"
date: 2026-11-14
theme: oversight-and-safety
evidence: [999b562dd3f5608a]
---
SwarmSafe-Delta asks whether an upstream agent's message changed the executor's action. It freezes upstream computation and varies only delivery: real, hidden, or a format-matched placebo. It then scores one committed action against deterministic benign and risky policy states.

Across four models on constructed tasks, real delivery produced 21.4% risky-world violations, against 5.0% with placebo and 1.0% hidden. Real delivery also improved benign success. In a regime that requires an upstream lookup, it raised safe completion by 74.2 points over hidden, so cutting communication costs utility.

The effect depended on whether the message recommended a prerequisite check or direct execution. The authors frame this as a measurement protocol, not a natural failure rate.

For builders: inter-agent messages are an attack and error surface. Test them with placebo controls.
