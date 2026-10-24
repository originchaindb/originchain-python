# originchain (Python)

Official Python client for [OriginChain](https://originchain.ai).

> Other languages: TypeScript / JavaScript → [`@originchain/sdk` preview](https://github.com/originchaindb/originchadb/releases/tag/v0.7.0-rc.3) · Go → [`github.com/originchaindb/originchaindb-go` preview](https://github.com/originchaindb/originchaindb-go/releases/tag/v0.2.0-rc.2) · raw HTTP → [HTTP API reference](https://originchaindb.com/docs/api).

## Install

This branch prepares the `0.10.0rc3` GitHub preview with sync/async query
metrics and native async namespace parity. Install its release wheel after the preview is published:

```bash
pip install "https://github.com/originchaindb/originchain-python/releases/download/v0.10.0-rc.3/originchain-0.10.0rc3-py3-none-any.whl"
```

The registry command below installs the latest stable PyPI version, which may
not include this preview's query metrics or async namespaces:

```bash
pip install originchain
```

HTTP/2 is enabled by default - multiplexed cross-region calls save ~300 ms each vs HTTP/1.1.

## Quick start

```python
from originchain import OriginChain

# Reads OC_BASE_URL, OC_BEARER, OC_TENANT from env.
db = OriginChain.from_env()

# Register a schema.
db.schemas.register(open("orders.toml").read())

# Insert a row.
db.rows.put(
    "trading.orders",
    {"order_id": "o1", "symbol": "AAPL", "qty": 100},
    idempotency_key="user-action-42",
)

# Ask in natural language.
result = db.ask("orders for AAPL above 50 shares last week")
for row in result["rows"]:
    print(row)
```

## Query metrics

Both clients provide `query_metrics(minutes=60, bucket_seconds=60)` using the
same authentication, timeout and safe-read retry settings as other requests.
The response is a typed dictionary (`QueryMetricsResponse` with
`QueryMetricsBucket` entries) retaining the server's field names:

```python
with OriginChain.from_env() as db:
    metrics = db.query_metrics()  # 60 minutes, 60-second buckets
    print(metrics["from"], metrics["to"])  # Unix milliseconds, Python integers
    for bucket in metrics["buckets"]:
        rate = bucket["calls"] / bucket["observed_seconds"]
        print(rate, bucket["mean_latency_ms"])  # None when calls == 0

```

For async applications:

```python
from originchain import AsyncOriginChain

async def read_daily_metrics():
    async with AsyncOriginChain.from_env() as db:
        return await db.query_metrics(minutes=1440, bucket_seconds=600)
```

Supported minute/bucket-second pairs are `60/60`,
`1440/600` and `10080/3600`; the server rejects unsupported pairs. Coverage is
clipped to collection start and retention, so use `observed_seconds` for
throughput. Counts and millisecond timestamps preserve Python integer
precision; idle mean latency stays `None`, not a fabricated zero.

This is a `local-process` view of completed execution requests, not an
aggregate across replicas or a count of individual SQL statements. Restart
clears history. A tenant service credential or query administrator is required;
impersonated database-user headers are refused with HTTP 403. The client
preserves authorization errors and HTTP 503 incomplete-coverage failures.

## Async

```python
import asyncio
from originchain import AsyncOriginChain

async def main() -> None:
    async with AsyncOriginChain.from_env() as db:
        await db.rows.put("trading.orders", {"order_id": "o2", "symbol": "MSFT", "qty": 50})
        print(await db.ask("show me the largest MSFT order this hour"))

asyncio.run(main())
```

Both clients expose `schemas`, `rows`, `sql`, `vector`, `fts`, `graph`, and
`admin` with the same operation names, arguments and result models. With
`AsyncOriginChain`, await each network operation, including `db.sql.query`,
`db.vector.topk`, and the extended graph algorithms. Legacy calls such as
`await db.sql(...)`, `await db.sql_one(...)`, `await db.vector_topk(...)` and
`await db.fts_search(...)` keep their existing response shapes. Availability of
each operation still depends on engine support, feature flags and privileges.

```python
async with AsyncOriginChain.from_env() as db:
    result = await db.sql.query(
        "SELECT * FROM trading.orders WHERE symbol = $1", ["MSFT"]
    )
    print(result.rows)
    accepted = await db.rows.put_batch(
        "trading.orders",
        ({"order_id": f"import-{i}", "symbol": "MSFT", "qty": i} for i in range(500)),
        chunk=100,
        idempotency_key="orders-import-20261024",
    )
```

Async `rows.put_batch` also accepts an async iterable. It consumes one chunk at
a time and sends chunks sequentially, with distinct keys such as
`orders-import-20261024-c0` and `orders-import-20261024-c1`. The returned count is
the total accepted by the server. Failures and cancellation propagate; earlier
chunks may already be durable, and later chunks are not consumed or sent.
Writes are not automatically retried. After checking the server outcome, a
caller replaying a batch must keep the same base key, row ordering and chunk
size; server idempotency retention still applies.

## SQL

```python
# Typed surface (recommended). Bind parameters are POSITIONAL: pass a
# list whose order matches the $1, $2, ... placeholders.
result = db.sql.query(
    "SELECT order_id, qty FROM trading.orders WHERE symbol = $1 AND qty > $2",
    params=["AAPL", 50],
)
for row in result.rows:
    print(row["order_id"], row["qty"])
print(result.columns)  # ["order_id", "qty"]

# Execution counts are reported by the server; None means unknown:
exec_result = db.sql.execute("INSERT INTO trading.orders ...")
print(exec_result.kind, exec_result.rows_affected)
```

The legacy callable `db.sql("SELECT ...")` still works and returns the
tagged-union dataclass. `db.sql_one("SELECT ... LIMIT 1")` returns the
first row dict (or `None`).

`SqlInsert.inserted`, `SqlDelete.rows_affected`, and
`SqlExecResult.rows_affected` preserve server-reported counts, including zero.
Earlier engines may return a translation without a count; the SDK reports
`None` in that case and never replays the write automatically. A separate
`rows_buffered` count means an open transaction still requires a commit.
Check these fields before claiming that a write or deletion succeeded.

> **Parameters are positional, not named.** The engine binds `$1` / `$2`
> by index; there is no named-parameter binder. Passing a `dict` raises
> `OCValidationError` with the positional rewrite in the message rather
> than guessing an order for you.

## Vector

```python
# Typed surface (recommended): `dim` is derived from the vector length.
db.vector.put("embeddings", "doc-1", [0.1, 0.2, 0.3], metadata={"src": "wiki"})
hits = db.vector.topk(
    "embeddings",
    [0.1, 0.2, 0.3],
    k=5,
    metric="cosine",
    filter={"src": "wiki"},   # optional metadata filter
    nprobe=8,                  # optional IVF tuning knob
)
for h in hits:
    print(h.vec_id, h.score, h.metadata)

db.vector.delete("embeddings", "doc-1")

# Pre-install IVF centroids for cold-start tables:
res = db.vector.install_centroids("embeddings", centroids=[[...], [...]])
print(res.installed, res.partitions, res.dim)
```

The legacy `db.vector_put(...)` / `db.vector_topk(...)` methods stay
available for code written before the typed namespace landed.

## Full-text

```python
db.fts.index("articles", "body", "d1", "the quick brown fox")

# BM25 with highlight snippets + facet aggregation.
result = db.fts.search(
    "articles",
    "body",
    "quick fox",
    mode="bm25",
    fuzzy=1,
    highlight=True,
    facets=["color", "brand"],
)
for h in result.hits:
    print(h.doc_id, h.score, h.highlights)
print(result.facets)  # {"color": [FacetBucket(value="red", count=3), ...]}

# Per-(table, field) admin:
db.fts.install_synonyms("articles", "body", {"car": ["auto", "vehicle"]})
db.fts.install_stopwords("articles", "body", ["the", "a", "an"])
```

`db.fts_index(...)` / `db.fts_search(...)` remain for back-compat.

## Graph

```python
# Single-hop neighbours + BFS:
nbrs   = db.graph.neighbors_of("users", "u1", "follows")
bfs    = db.graph.bfs_of("users", "u1", "follows", max_depth=3)

# Shortest path + Yen's K-shortest:
path   = db.graph.shortest_path("users", "u1", "u9", "follows")
ranked = db.graph.k_shortest("users", "u1", "u9", "follows", k=5,
                             weight_col="edge_weight")

# Random walk (uniform; p/q != 1 routes through Node2Vec-biased):
walk = db.graph.random_walk("users", "u1", "follows", steps=10, seed=42)

# Community detection + centrality:
communities = db.graph.louvain("users", "follows")
labels      = db.graph.label_propagation("users", "follows", seed=1)
ranks       = db.graph.pagerank("users", "follows", nodes=["u1", "u2", "u3"])
between     = db.graph.betweenness("users", "follows")
```

The legacy kwarg-style helpers (`db.graph.neighbors(...)`,
`db.graph.bfs(...)`, `db.graph.path(...)`, `db.graph.dijkstra(...)`,
`db.graph.reverse_neighbors(...)`) stay available.

## Auth

Bearer tokens are minted in the OriginChain console and scoped to a
single instance. Treat them like database passwords - env vars or
secrets manager, never committed.

## Errors

The client maps HTTP errors to a typed hierarchy:

```python
from originchain import (
    OCAuthError,
    OCPaymentRequiredError,
    OCRateLimitedError,
    OCServerError,
    OriginChainBadRequest,   # alias of OCValidationError (4xx)
    OriginChainServerError,  # alias of OCServerError    (5xx)
)

try:
    db.rows.put("trading.orders", row)
except OCRateLimitedError as e:
    time.sleep(e.retry_after)
    db.rows.put("trading.orders", row)
except OCPaymentRequiredError as e:
    print(f"enable {e.name} at {e.purchase_url}")
except OriginChainBadRequest:
    print("bad request — fix it before retrying")
except OCAuthError:
    print("rotate your bearer in the console")
```

When the leader returns 200 but synchronous replication didn't ack
within the configured timeout, the client emits an
`OCReplicationDegraded` warning. The write IS durable on the leader;
the warning surfaces a follower-lag signal callers can monitor or page
on.

Every `OCError` carries two ids:

- `request_id` is the engine's id for the request (`X-OC-Request-Id`). Include
  it in a support request: it identifies the exact record on your engine.
- `logical_request_id` is the id the client sent with the call
  (`X-OC-Logical-Request-Id`, a UUID). It stays the same on every retry of the
  call, while `X-OC-Attempt` counts 1, 2, ... The engine records both next to
  its own id.

```python
from originchain import OCError

try:
    db.sql("SELECT * FROM shop.orders")
except OCError as e:
    log.error("query failed: %s (request %s)", e, e.request_id)
```

## Diagnostics

Diagnostics are off by default. Turn them on to let OriginChain support see what
your application saw of its calls, not only what the engine saw:

```python
db = OriginChain.from_env(diagnostics=True)          # or AsyncOriginChain
```

With diagnostics on, the client reports each attempt of each call to your own
engine, with your bearer token, from a background thread (or task, for the
async client):

- the method and path, the outcome and duration;
- the HTTP status received, or that the request was not sent or got no response;
- the request ids above, and the engine's error code when it returned one.

The engine keeps only its route template for the path (for example
`/v1/tenants/:tenant/vector/:table/topk`), so table, key and index names stay on
your engine. Query strings are removed before anything is queued. SQL,
parameters, row data, search text, error messages and keys are never sent.

Reporting never slows or fails your calls. Reports wait in a small bounded
queue and are sent at most once a second; a report that cannot be sent is
dropped. `close()` / `aclose()` send what is still queued; call
`flush_diagnostics()` to send it earlier.

## What's new in 0.5

0.5.0 wires up the engine endpoints that shipped after the
typed-namespace batch. All new methods are additive — no
breaking changes — and require an engine deployed at commit
`2c1fe55a` or later. The examples below use the typed namespaces and
use the synchronous client; with `AsyncOriginChain`, await the same methods.

### Vector: bulk delete + IVF lifecycle

```python
# Single delete: now actually works end-to-end. 0.4 was wire-ready but
# the Rust handler hadn't shipped; missing-row returns deleted=False
# (200), not 404, so cleanup loops never need try/except.
result = db.vector.delete("embeddings", "doc-1")
print(result.deleted)

# Bulk delete (up to 10 000 ids per call, one WAL frame):
result = db.vector.delete_bulk("embeddings", ["doc-1", "doc-2", "doc-3"])
print(result.deleted_count, result.missing_count)

# IVF centroid lifecycle — bootstrap an IVF table after a row of writes:
db.vector.train_and_install_centroids("embeddings", partitions=64, seed=42)
preview  = db.vector.centroids("embeddings")           # installed? sample?
status   = db.vector.rebalance_status("embeddings")    # skew + action hint
```

### Graph: Node2Vec topk + GraphSAGE

```python
# Top-k similar nodes against persisted Node2Vec embeddings:
hits = db.graph.node2vec_topk("users", "follows", "u1", k=10)

# GraphSAGE attribute-aware embeddings (train + optionally persist):
res = db.graph.graphsage(
    "users",
    feature_col="profile_vec",
    rel="follows",
    config={"embedding_dim": 128, "epochs": 5, "seed": 42},
    persist=True,
)
print(res.vocab_size, res.final_loss, res.persisted)

# Persisted-embedding similarity (same shape as node2vec_topk):
hits = db.graph.graphsage_topk("users", "follows", "u1", k=10)
```

### SQL: materialized views

```python
res = db.sql.install_materialized_view(
    "daily_orders",
    "SELECT order_id, qty FROM trading.orders",
    refresh_mode="on_demand",   # default
)
print(res.rows_materialized, res.bytes_written, res.refresh_ts)

# Full recompute — atomically overwrites the snapshot:
db.sql.refresh_materialized_view("daily_orders")

# Snapshot read:
view = db.sql.read_materialized_view("daily_orders")
for row in view.rows:
    print(row)
```

`refresh_mode` accepts exactly two values:

| value | behaviour |
| --- | --- |
| `"on_demand"` (default) | The snapshot only changes when you call `refresh_materialized_view()`, which fully recomputes it. This is the mode to build against today. |
| `"incremental"` | Apply-time maintenance as source rows are written. **Aggregate** views are behind a preview flag that ships OFF, so an incremental view over an aggregate query currently fails with `422`. |

Anything else raises `OCValidationError` before the request is sent.

### Admin: per-tenant replication config

```python
# Install / change the replication topology for one tenant:
db.admin.install_tenant_config(tenant_id, replication_mode="raft_quorum")

# Read the installed mode (returns active_passive when none installed):
cfg = db.admin.get_tenant_config(tenant_id)
print(cfg.replication_mode, cfg.installed)
```

### FTS lemmatization

No SDK API change — `db.fts.install_synonyms(...)` /
`install_stopwords(...)` are unchanged. Server-side, the analyzer now
applies dictionary-based lemmatization across 9 languages when the
table's analyzer config selects `lemmatizer="dictionary"`.

## Versioning

This client follows semver. The `0.x` line is for design partners;
the API surface may change before `1.0`.


## Database identity (v0.9.0)

Pass both database identity values alongside your instance bearer token. They
become `X-OC-DB-User` and `X-OC-DB-Key` on engine requests, including diagnostics.
They do not replace the instance bearer or grant permissions. Keep credentials
in your application's secret store; never hard-code them in browser bundles.
Omit both options for the existing bearer-only behavior. Partial/invalid pairs
are rejected. Identity-bearing requests do not follow redirects.

```
OriginChain(base_url=endpoint, bearer=instance_token, tenant=tenant_id,
            db_user=db_user, db_key=db_key)
```

## Weighted graph traversal

Dijkstra `weights` maps directed node pairs to numeric weights, for example
`{"u1|u2": 1.5, "u2|u3": 0.5}`, for an existing relation with those edges.
The keys are not column names. Missing pairs skip edges; an empty map does not
assign unit weights. An unreachable destination returns `{"cost": null}`.
The result is a nullable cost, not an ordered path. The path endpoint reports unweighted reachability. See https://originchaindb.com/docs/graph.

## Retry policy and migration

Sync and async clients default to at most three **additional** attempts on GET,
HEAD and OPTIONS. `max_retries=0` disables retries; valid values are integers
0..99. **Behavior change:** SQL and other mutation methods no longer retry
automatically. Earlier versions could replay writes whose endpoints did not
implement idempotency, even though a key was attached.

SQL requires an explicit assertion that repeating the operation is safe:

```python
with OriginChain(base_url=base_url, bearer=bearer, tenant=tenant,
                 max_retries=2, max_retry_time=30) as db:
    row = db.sql_one("SELECT $1", [7], retry_safe=True)

async with AsyncOriginChain(base_url=base_url, bearer=bearer, tenant=tenant,
                            max_retries=2, max_retry_time=30) as db:
    row = await db.sql_one("SELECT $1", [7], retry_safe=True)
```

The callable `sql`, `sql_one`, and `sql.query` accept positional parameters,
`retry_safe`, and `idempotency_key`. A key alone is not permission to replay SQL.
Do not set `retry_safe=True` for writes without verifying their replay semantics.
Both clients apply the same retry policy to their typed namespaces.

Eligible calls retry transport errors and HTTP 429/500/502/503/504. Backoff uses
full jitter with a 250 ms exponential cap growing to 4 seconds. `Retry-After`
accepts integer seconds (including zero) or an HTTP date; invalid values fall
back to jitter. A server delay that does not fit the retry window returns the
last error instead of retrying early.

`max_retry_time` defaults to 30 seconds and bounds **scheduling of retries and
waits**, not an in-flight HTTP request. HTTPX's `timeout` still controls individual
network phases; it is not a whole-call deadline. Async applications can use
`asyncio.wait_for` for an overall deadline, and cancellation interrupts backoff.
Logical request IDs and idempotency keys stay stable, with one diagnostic event
per attempt. Avoid stacking another retry policy in a custom HTTP transport.

## Compatibility and verification

Python 3.9+ is supported. CI runs the shared sync/async contract suite on Linux
with Python 3.9, 3.12 and 3.14, plus Windows and macOS with Python 3.12. Every
job builds and installs the wheel into a fresh virtual environment and checks
the typing marker and public async operations. Async cancellation stops local
work and future retries; an in-flight write may already have reached the server.

`tests/e2e_smoke.py` registers an isolated namespace using `OC_NS` and requires
working credentials when `OC_REQUIRE_LIVE=1`. It checks sync operations and
native async batching, positional SQL, confirmed deletion plus absence,
vector search, full-text search and graph traversal. Administrative mutations
and all optional advanced engine features are covered by transport contracts,
not by this live smoke.

The default `OC_E2E_ASK_STATUS=200` requires successful Ask execution. An
explicit `OC_E2E_ASK_STATUS=402` validates only the exact `ask_unavailable`
response on a tenant without Ask enabled; it does not validate successful Ask
execution. Other statuses, other error codes and unexpected success fail the
selected profile. GitHub E2E reads this setting from the repository variable of
the same name; leave it unset for the default full profile.
The stable release workflow always requests the full `200` profile, overriding
the repository variable, and cannot promote an Ask-unavailable run.

The 24 October 2026 candidate passed 441 offline tests and 19 live acceptance
checks on the explicit Ask-unavailable profile. Successful Ask execution is
still unverified. Four older optional live pytest checks were skipped during
the offline suite; they are separate from the 19-check live runner.
