# Python SDK 0.10.0rc4

Fixes a response decoder error after successful bulk SQL DELETE operations. The server can return `kind`, `schema` and `rows_affected` without a single `pk`; the synchronous and asynchronous clients now return `SqlDelete(pk=None, ...)` instead of raising `KeyError`.

Single-key results retain their key. Execution counts remain server-reported: zero is zero, an absent count is unknown, and buffered rows are separate from committed rows.

This is a GitHub prerelease. The package retains its MIT license. Existing release tags and assets are unchanged; no registry upload is included.

```bash
python -m pip install "https://github.com/originchaindb/originchain-python/releases/download/v0.10.0-rc.4/originchain-0.10.0rc4-py3-none-any.whl"
```
