---
title: "Agent-speed cloud spend outruns billing alerts that lag about a day"
date: 2026-07-16
theme: execution-and-identity
evidence: [6f5c728ce100a70f]
---
A three-person agency got a **$14,000 AWS bill in one day** after attackers extracted static access keys with unrestricted Bedrock access and burned them on Claude calls. In the DN42 incident, an autonomous agent with open-ended AWS access provisioned **$6,531 of oversized infrastructure in 24 hours**. A credit-card charge caught both, because Cost Explorer and Budgets work off data that lags roughly a day.

The fix is scoped credentials and action-time alerts applied to spend: IAM roles instead of static keys, service-control policies blocking expensive instance families, and CloudTrail alerts on `RunInstances` and `InvokeModel`.
