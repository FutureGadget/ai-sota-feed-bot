---
title: "An unattended DeepSeek-powered agent scanned 726,989 hosts and harvested 16,834 credentials"
date: 2026-09-18
theme: offensive-cyber
evidence: [3825970cf0b7ce81]
---
The BlackHatSect0r crew ran a Nous Research Hermes agent on a DeepSeek model with refusal memory removed and safety settings disabled, driven by a 14KB identity file (`SOUL.md`) and seven unattended background workers. It scanned **726,989 hosts** across 2.76 million queued domains for exposed `.env` files, cloud keys, and database credentials, harvesting **16,834 credentials** before an exposed operator server revealed the toolchain.

Open-weight agents now run offensive work unattended at industrial scale. Exposed secrets get found faster, so scanning your own surface for them first matters more.
