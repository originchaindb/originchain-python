# OriginChainDB Python SDK 0.10.0rc2

This GitHub preview adds native async SQL, vector, full-text, graph and admin
namespaces, alongside streaming row batches. The existing callable SQL API and
legacy async convenience methods retain their result shapes.

Async batches accept ordinary and async iterables, send bounded chunks
sequentially, and derive distinct idempotency keys from the input chunk index.
Failure or cancellation stops later work. Earlier chunks may already be
durable; writes are never automatically retried.

SQL INSERT and DELETE results now preserve the server's execution counts.
`sql.execute().rows_affected` is `None` when the server did not confirm a count,
replacing an incorrect inferred value of one. Transaction-buffer counts are
reported separately and do not imply a commit.

Verification before this preview:

- 441 offline tests passed; four optional legacy live pytest checks were skipped.
- Ruff passed and type checking found no issues in the ten SDK modules.
- The isolated live runner passed 19 checks, including native async batching,
  positional SQL, confirmed deletion and subsequent absence, vector search,
  full-text search, and graph traversal.
- That live run used the explicit HTTP 402 `ask_unavailable` profile.
  Successful Ask execution remains unverified; stable release promotion still
  requires the full HTTP 200 Ask profile.
- Compatibility CI covers Linux Python 3.9/3.12/3.14 and Windows/macOS Python
  3.12, with wheel building and fresh-install checks in every job. The release
  verification receipt records the results for the final commit.

Install the preview from its GitHub release asset:

```bash
pip install "https://github.com/originchaindb/originchain-python/releases/download/v0.10.0-rc.2/originchain-0.10.0rc2-py3-none-any.whl"
```

This preview is not a stable PyPI promotion. Advanced optional engine features
and privileged admin mutations have transport-contract coverage; the live
smoke does not exercise every such operation.
