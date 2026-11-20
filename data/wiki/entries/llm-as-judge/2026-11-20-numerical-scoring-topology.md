---
title: "A judge's scale width, offset, and granularity move its scores and calibration, most on judgment-heavy tasks"
date: 2026-11-20
theme: scoring-design
evidence: [4c7f163e7f53327e]
also: [agent-evaluation]
---
This study defines *numerical scoring topology*: a scoring scheme's width, granularity, offset, symmetry, and boundary placement. Across benchmarks and judge models, changing only the topology systematically moved zero-shot judge scores, calibration, and robustness. **Shifted and narrow ranges caused some of the largest deviations**, and judgment-heavy evaluations were hit hardest. Larger, stronger judges were more robust.

For builders: the scale is part of the judge. Changing 1-5 to 0-10 mid-project breaks comparability with earlier runs, and small judges need a fixed, standard scale more than large ones do.
