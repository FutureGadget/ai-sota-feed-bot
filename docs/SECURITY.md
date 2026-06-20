# SECURITY.md

## Secret management
- Use GitHub Actions Secrets for all credentials
- Never store tokens in code/config tracked by git
- Rotate exposed tokens immediately

## Hardening backlog
- Secret scanning gate in CI
- Minimal bot permissions review
- Optional outbound request allowlist
