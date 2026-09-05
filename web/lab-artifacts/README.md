# Agent Skill Lab artifacts

Edition zero has no experiment artifacts because it publishes only the protocol.
Result editions place reviewed, public evidence under a directory named for the
Lab slug. Never place secrets, private repository content, subscriber data, or
hidden model reasoning here.

Only inert `.json`, `.jsonl`, `.md`, and `.txt` files are accepted. The deploy
stages referenced files only and serves them with a sandboxing Content Security
Policy and MIME-sniffing disabled.

`pipeline/build_skill_lab.py` refuses to publish a record when a referenced
same-origin file is missing. It also verifies the SHA-256 digest for pinned
skill and instruction files. The Vercel build stages validated references at
`/lab-artifacts/` and `/web/lab-artifacts/`.
