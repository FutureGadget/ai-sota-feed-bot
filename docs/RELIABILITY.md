# RELIABILITY.md

## Reliability goals
- Daily digest workflow success rate >= 99%
- Graceful degradation when a source fails
- No hard failure when Telegram secrets are absent

## Operational checks
- Monitor workflow runs daily
- Keep ingest and publish steps independently retryable
