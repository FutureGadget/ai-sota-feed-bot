# RELIABILITY.md

## Reliability goals
- Daily digest workflow success rate >= 99%
- Graceful degradation when a source fails
- No hard failure when Telegram secrets are absent

## Operational checks
- Monitor workflow runs daily
- Keep ingest and publish steps independently retryable
- Track per-source success/failure and stale-source risk via `data/health/source_health.json`
- Use circuit breaker state (`data/health/circuit_breaker.json`) to suppress repeatedly failing sources during cooldown
