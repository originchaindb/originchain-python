"""Install the built wheel in a fresh venv and check its public async surface."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def verify_installed() -> None:
    import httpx
    import originchain
    from originchain import AsyncOriginChain

    package = Path(originchain.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()), "imported source checkout"
    assert (package / "py.typed").is_file(), "missing PEP 561 marker"
    assert (package / "_async_namespaces.py").is_file(), "missing async namespaces"
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/_batch"):
            return httpx.Response(200, json={"inserted": len(json.loads(request.content))})
        if request.url.path.endswith("/sql"):
            if json.loads(request.content)["sql"].startswith("DELETE"):
                return httpx.Response(200, json={
                    "kind": "delete", "schema": "demo.rows", "pk": "one", "rows_affected": 1,
                })
            return httpx.Response(200, json={"kind": "select", "rows": [{"id": "one"}]})
        if request.url.path.endswith("/delete-bulk"):
            return httpx.Response(200, json={"deleted_count": 1, "missing_count": 0})
        if request.url.path.endswith("/k-shortest"):
            return httpx.Response(200, json={"paths": [{"nodes": ["one", "two"], "cost": 1}]})
        if "/fts/" in request.url.path:
            return httpx.Response(200, json=[{"doc_id": "one", "score": 1}])
        return httpx.Response(200, json={"replication_mode": "active_passive"})

    real = httpx.AsyncClient
    httpx.AsyncClient = lambda **kwargs: real(**kwargs, transport=httpx.MockTransport(handler))

    async def smoke():
        async with AsyncOriginChain(
            base_url="https://engine.invalid", bearer="test", tenant="test", verify=False,
        ) as db:
            assert (await db.sql("SELECT * FROM demo.rows")).rows == ({"id": "one"},)
            assert (await db.sql.query("SELECT * FROM demo.rows")).rows == [{"id": "one"}]
            assert (await db.sql.execute("DELETE FROM demo.rows WHERE id='one'")).rows_affected == 1
            assert await db.rows.put_batch("demo.rows", [{"id": "one"}], chunk=1) == 1
            assert (await db.vector.delete_bulk("embeddings", ["one"])).deleted_count == 1
            assert (await db.fts.search("docs", "text", "example")).hits[0].doc_id == "one"
            assert await db.graph.shortest_path("nodes", "one", "two", "follows") == ["one", "two"]
            assert (await db.admin.get_tenant_config("test")).replication_mode == "active_passive"
        assert db._client.is_closed

    try:
        asyncio.run(smoke())
    finally:
        httpx.AsyncClient = real
    assert len(requests) == 8
    print("Fresh wheel install: typing marker and 8 public async operations passed")


def main() -> None:
    if sys.argv[1:] == ["--installed"]:
        verify_installed()
        return
    root = Path(__file__).resolve().parents[1]
    wheels = [Path(sys.argv[1]).resolve()] if len(sys.argv) == 2 else list((root / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one built wheel in dist/")
    if not wheels[0].is_file() or wheels[0].suffix != ".whl":
        raise SystemExit("Expected a wheel file")
    with tempfile.TemporaryDirectory(prefix="originchain-wheel-") as tmp:
        env = Path(tmp) / "venv"
        venv.EnvBuilder(with_pip=True).create(env)
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheels[0])], check=True, cwd=tmp)
        subprocess.run([str(python), "-I", str(Path(__file__).resolve()), "--installed"],
                       check=True, cwd=tmp)


if __name__ == "__main__":
    main()
