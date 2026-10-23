# OriginChain Python SDK 0.10.0

This release adds conservative retries with bounded waits, HTTP-date Retry-After
support, stable logical request IDs and idempotency keys, and per-attempt diagnostics.
SQL requires an explicit assertion that replay is safe. A key alone does not prove
that a server endpoint deduplicates writes.

Migration: SQL and mutation methods no longer retry automatically. Safe GET,
HEAD and OPTIONS calls retain up to three additional attempts. Set retry_safe=True
only for SQL operations that can safely run again. max_retry_time bounds retry
scheduling, while HTTPX phase timeouts still control in-flight requests.

Sync and async SQL now accept positional parameters and caller idempotency keys.
The wheel includes py.typed. Batch idempotency keys follow input chunk order, and
invalid batch sizes fail before consuming input or sending requests.
