# OriginChainDB for Python

The `originchain` package provides synchronous and asynchronous clients for OriginChainDB, with typed namespaces for SQL, rows, vector search, full-text search and graph operations.

[Documentation](https://originchaindb.com/docs/sdk/python) | [Changelog](CHANGELOG.md) | [Issues](https://github.com/originchaindb/originchain-python/issues) | [Other languages](https://github.com/originchaindb)

## Installation

Requires Python 3.9 or later. Install the current GitHub preview:

```sh
python -m pip install "https://github.com/originchaindb/originchain-python/releases/download/v0.10.0-rc.3/originchain-0.10.0rc3-py3-none-any.whl"
```

Version `0.10.0rc3` is a prerelease. `pip install originchain` may select an older PyPI version with a smaller async API. Async support and HTTP/2 dependencies are included; no extra is required. Checksums are on the [release page](https://github.com/originchaindb/originchain-python/releases/tag/v0.10.0-rc.3).

## Your first query

Set the connection details for one database in your environment:

| Variable | Value |
| --- | --- |
| `OC_BASE_URL` | Full database HTTPS endpoint |
| `OC_TENANT` | Tenant ID from the same connection details |
| `OC_BEARER` | Instance bearer token |

Save this as `query.py` and run `python query.py`. It needs no tables or sample data.

```python
from originchain import OriginChain

with OriginChain.from_env() as db:
    result = db.sql.query(
        "SELECT $1 AS message",
        params=["Hello from OriginChainDB"],
    )
    for row in result.rows:
        print(row["message"])
```

Reuse a client across requests to reuse its HTTP connections. The context manager closes it; otherwise call `close()` when finished.

If your database requires user identity, provide both values alongside the instance bearer:

```python
import os
from originchain import OriginChain

with OriginChain.from_env(
    db_user=os.environ["OC_DB_USER"],
    db_key=os.environ["OC_DB_KEY"],
) as db:
    print(db.sql_one("SELECT $1 AS value", [7]))
```

The two credentials add database-user headers; they do not replace the bearer token. Omit both for a bearer-only connection. `from_env()` reads the three connection variables above; pass optional settings as keyword arguments.

## Async applications

`AsyncOriginChain` has the same operation namespaces. Await network calls and use `async with` to close the client:

```python
import asyncio
from originchain import AsyncOriginChain

async def main():
    async with AsyncOriginChain.from_env() as db:
        result = await db.sql.query("SELECT $1 AS message", ["Hello from async Python"])
        print(result.rows)

asyncio.run(main())
```

For an overall deadline, wrap a call in `asyncio.wait_for`. Cancellation interrupts local work and retry waits; a write may already have reached the server.

## SQL and rows

The examples below assume `quickstart.products` from the [database quickstart](https://originchaindb.com/docs/quickstart). Each block reuses an open `db` client.

```python
result = db.sql.query(
    "SELECT id, name, price_cents FROM quickstart.products "
    "WHERE price_cents < $1 LIMIT 10",
    params=[2000],
)
for row in result.rows:
    print(row["id"], row["name"])
```

Parameters are positional: lists bind `$1`, `$2` and so on. Dictionaries are rejected. Bind values instead of inserting them into SQL strings. Keep table and column names under application control.

Use `db.sql.execute(...)` for execution results and `db.sql_one(...)` for one row or `None`. The older callable `db.sql(...)` remains available and returns a tagged result. Server-reported write counts can be zero or `None`; an absent count is unknown. `rows_buffered` is separate from committed execution.

Known issue in `0.10.0rc3`: a bulk DELETE can succeed and then raise `KeyError('pk')` while decoding the response. Check the database outcome before retrying the write.

For row APIs and batches:

```python
db.rows.put("quickstart.products", {
    "id": "product-001", "name": "Trail mug", "price_cents": 1500,
})

accepted = db.rows.put_batch(
    "quickstart.products",
    ({"id": f"product-{i}", "name": f"Item {i}", "price_cents": 1000}
     for i in range(10, 30)),
    chunk=10,
    idempotency_key="catalog-import-001",
)
print(accepted)
```

Batches are sent sequentially. Async batches also accept async iterables. Each chunk receives a distinct key derived from the base key. Failure or cancellation stops later chunks; earlier chunks may already be durable. Before replaying a batch, check the server outcome and keep the same base key, ordering and chunk size. Deduplication depends on the endpoint and its retention window.

## Vector and full-text search

The SDK accepts embeddings supplied by your application. Use a table configured for the chosen vector dimensions and metric:

```python
db.vector.put("quickstart.products", "product-001", [0.1, 0.2, 0.3])
hits = db.vector.topk("quickstart.products", [0.1, 0.2, 0.3], k=5, metric="cosine")
for hit in hits:
    print(hit.vec_id, hit.score)
```

Prepare the field using the [full-text guide](https://originchaindb.com/docs/fts), then index and search it:

```python
db.fts.index("quickstart.products", "name", "product-001", "Trail mug")
result = db.fts.search("quickstart.products", "name", "trail", mode="bm25", k=5)
for hit in result.hits:
    print(hit.doc_id, hit.score)
```

## API namespaces

| Namespace | Operations | Reference |
| --- | --- | --- |
| `db.schemas` | Register and inspect table schemas | [Schemas](https://originchaindb.com/docs/schemas) |
| `db.rows` | Read, write and batch rows | [Insert data](https://originchaindb.com/docs/insert) |
| `db.sql` | Parameterized queries and execution; materialized views | [SQL](https://originchaindb.com/docs/sql) |
| `db.vector` | Vector storage, search, deletion and index controls | [Vector search](https://originchaindb.com/docs/vector) |
| `db.fts` | Indexing, search and text-analysis controls | [Full-text search](https://originchaindb.com/docs/fts) |
| `db.graph` | Traversals, shortest-path costs and graph algorithms | [Graphs](https://originchaindb.com/docs/graph) |
| `db.admin` | Privileged engine configuration | [HTTP API](https://originchaindb.com/docs/api) |

These namespaces exist on both clients. Operations require the corresponding engine feature and permissions. The [client source](originchain/client.py) and [typed namespaces](originchain/_namespaces.py) define the Python signatures. Graph relations must be registered before traversal; Dijkstra uses directed node-pair weights and returns a nullable cost rather than a path.

`db.ask(...)` requires Ask to be enabled for the database. Successful Ask execution is not part of this preview's live verification. Optional engine features and administrative mutations have different capability and permission requirements.

## Timeouts and retries

Pass these options to either constructor or `from_env()`:

| Option | Default | Meaning |
| --- | --- | --- |
| `timeout` | `30.0` seconds | HTTPX network-phase timeout |
| `max_retries` | `3` | Additional attempts for eligible requests; `0` disables retries |
| `max_retry_time` | `30.0` seconds | Budget for scheduling retry delays and attempts |
| `verify` | `True` | TLS certificate verification; accepts a CA bundle path |
| `diagnostics` | `False` | Report bounded request metadata to your database |

GET, HEAD and OPTIONS can retry automatically. SQL and writes do not. To retry a read-only SQL operation, opt in on that call:

```python
with OriginChain.from_env(max_retries=2, max_retry_time=15) as db:
    row = db.sql_one("SELECT $1 AS value", [7], retry_safe=True)
```

Set `retry_safe=True` only when repeating the operation is safe. An idempotency key alone is insufficient. Eligible calls retry transport failures and HTTP 429, 500, 502, 503 and 504, using jitter and `Retry-After`. The retry budget does not interrupt a request already in flight; use an application deadline when needed.

## Errors and diagnostics

```python
from originchain import OCError

try:
    result = db.sql.query("SELECT $1 AS value", [7])
except OCError as error:
    print(error.status, error.request_id, error.logical_request_id)
    raise
```

HTTP failures use `OCError` subclasses. Transport failures are wrapped in `OCError`, with the underlying HTTPX exception available as `error.__cause__`. `OCReplicationDegraded` is a warning about replication acknowledgement, not an `OCError`. Include the request ID in support reports and keep credentials and query data out of logs.

Diagnostics are opt-in and report request metadata to your own engine, excluding SQL text, parameters and row contents. Closing the client flushes pending reports.

## Query metrics

```python
with OriginChain.from_env() as db:
    metrics = db.query_metrics(minutes=60, bucket_seconds=60)
    for bucket in metrics["buckets"]:
        duration = bucket["observed_seconds"]
        rate = bucket["calls"] / duration if duration > 0 else None
        print(bucket["at"], rate, bucket["mean_latency_ms"])
```

Use service or query-administrator credentials without database-user impersonation headers. Supported `(minutes, bucket_seconds)` pairs are `(60, 60)`, `(1440, 600)` and `(10080, 3600)`. Metrics are process-local and reset on restart. Idle latency is `None`; timestamps are Unix milliseconds. The response uses typed dictionaries and preserves integer counts.

## Compatibility and development

CI covers Python 3.9, 3.12 and 3.14 on Linux, plus Python 3.12 on Windows and macOS. The [release page](https://github.com/originchaindb/originchain-python/releases/tag/v0.10.0-rc.3) contains package checksums and the scope of live database verification. The `0.x` API can change before 1.0.

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -e ".[dev]" build twine
python -m pytest -q
python -m ruff check originchain tests
python -m build
python -m twine check dist/*
```

Open an [issue](https://github.com/originchaindb/originchain-python/issues) with the SDK and Python versions, request ID and a small reproduction with credentials removed.

## License

[MIT](LICENSE).
