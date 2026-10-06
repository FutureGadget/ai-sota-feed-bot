---
title: "Modal and Decagon cut production inference latency by tuning speculation to their workload"
date: 2026-06-30
theme: serving-default
evidence: [62173e9d865bdec2]
---
Modal and Decagon describe how they reached state-of-the-art inference latency in production with speculative decoding, by **tuning the draft/verify pair to Decagon's actual traffic** rather than using a stock configuration.

The write-up frames speculation as a deployable latency win you can reproduce on your own stack, not a benchmark result. The lesson for builders is that the speedup depends on the workload, so measure it on your traces.
