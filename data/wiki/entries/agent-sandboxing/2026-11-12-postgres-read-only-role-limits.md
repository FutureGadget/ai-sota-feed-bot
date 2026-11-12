---
title: "A read-only Postgres role's settings are session defaults; only the GRANTs hold against an agent"
date: 2026-11-12
theme: permission-policy
evidence: [9ebc28a7a2621ca2]
also: [tool-use]
---
A reproducible run on PostgreSQL 17.11 checks what a careful read-only agent role stops.

- **Defaults, not limits:** the session can run `SET default_transaction_read_only = off` and `SET statement_timeout = 0`. Writes then fail only on missing GRANTs. `CONNECTION LIMIT` holds because it is a role attribute.
- **Wrapper bypass:** a tool that wraps SQL in `BEGIN TRANSACTION READ ONLY` loses to `COMMIT; DELETE ...` when the driver accepts stacked statements. On a role with write grants, all six rows were deleted.
- **Harmful reads:** `GRANT SELECT` covers every column, and `pg_catalog` exposes ungranted tables' schemas.

For builders: give the agent its own role with column-level grants and role-bound row-level security, send SQL as one prepared statement, and enforce time limits from a pooler or watchdog. Vendor-authored, plain Postgres.
