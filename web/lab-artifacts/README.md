# Agent Skill Lab artifacts

Edition zero has no experiment artifacts because it publishes only the protocol.
Result editions place reviewed, public evidence under a directory named for the
Lab slug. Never place secrets, private repository content, subscriber data, or
hidden model reasoning here.

`pipeline/build_skill_lab.py` refuses to publish a record when a referenced
same-origin file is missing. It also verifies the SHA-256 digest for pinned
skill and instruction files. The Vercel build stages this directory at
`/lab-artifacts/`.
