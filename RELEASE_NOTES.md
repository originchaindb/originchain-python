# OriginChainDB Python SDK 0.10.0rc3

This GitHub preview adds `query_metrics(minutes=60, bucket_seconds=60)` to the
synchronous and native async clients. Its exported typed dictionaries retain
server field names, Python integer precision for timestamps/counters, and
`None` for idle latency. Existing timeout, authentication, retry and error
handling apply to this safe read.

Supported windows are 60 minutes / 60 seconds, 1440 / 600 and 10080 / 3600.
Metrics describe the current process; restart clears history and results are
not aggregated across replicas. Divide calls by `observed_seconds` for
throughput over the actual coverage. Tenant service credentials or a query
administrator are required; impersonated database-user headers are refused.

The preview retains rc2's native async namespaces, bounded row batches and
truthful SQL affected-row counts. Verification includes shared sync/async
transport tests, fresh-wheel consumers, and read-only live checks of all three
metrics windows. Final test counts, exact artifact hashes and compatibility
CI results are recorded in the release verification receipt.

Install after its GitHub preview release has been published:

```bash
pip install "https://github.com/originchaindb/originchain-python/releases/download/v0.10.0-rc.3/originchain-0.10.0rc3-py3-none-any.whl"
```

This preview is not a stable PyPI promotion. Live acceptance uses the explicit
HTTP 402 `ask_unavailable` profile; successful Ask execution remains unverified.
Stable promotion still requires the full HTTP 200 Ask profile. Advanced
optional features and privileged admin mutations have transport coverage;
the live smoke does not exercise every such operation.
