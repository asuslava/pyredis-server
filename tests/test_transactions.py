"""Integration tests for Redis Transactions (MULTI, EXEC, DISCARD)."""

import asyncio
import pytest
from pyredis.protocol import parse, serialize
from pyredis.server import RedisServer


@pytest.fixture
async def server():
    # Use port 0 so the OS assigns a free random port
    srv = RedisServer(host="127.0.0.1", port=0)
    server_task = asyncio.create_task(srv.start())

    # Wait for server to bind and get actual port
    while srv._server is None or not srv._server.sockets:
        await asyncio.sleep(0.01)

    port = srv._server.sockets[0].getsockname()[1]
    yield port

    server_task.cancel()
    await asyncio.gather(server_task, return_exceptions=True)


async def send_cmd(reader, writer, cmd_name, *args):
    payload = serialize([cmd_name.encode(), *[a.encode() if isinstance(a, str) else a for a in args]])
    writer.write(payload)
    await writer.drain()

    buf = bytearray()
    while True:
        chunk = await reader.read(4096)
        buf.extend(chunk)
        res = parse(bytes(buf), 0)
        if res is not None and getattr(res, "__class__", None).__name__ != "Incomplete":
            val, _ = res
            return val


@pytest.mark.asyncio
async def test_transaction_multi_exec(server):
    port = server
    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # 1. Start MULTI
    assert (await send_cmd(reader, writer, "MULTI")).value == "OK"

    # 2. Commands are QUEUED
    assert (await send_cmd(reader, writer, "SET", "user", "Alice")).value == "QUEUED"
    assert (await send_cmd(reader, writer, "GET", "user")).value == "QUEUED"
    assert (await send_cmd(reader, writer, "LPUSH", "tasks", "t1")).value == "QUEUED"

    # 3. EXEC executes all and returns array of results
    results = await send_cmd(reader, writer, "EXEC")
    assert len(results) == 3
    assert results[0].value == "OK"
    assert results[1] == b"Alice"
    assert results[2] == 1

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_transaction_discard(server):
    port = server
    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    await send_cmd(reader, writer, "MULTI")
    assert (await send_cmd(reader, writer, "SET", "k", "v")).value == "QUEUED"

    # DISCARD cancels transaction
    assert (await send_cmd(reader, writer, "DISCARD")).value == "OK"

    # "k" should NOT have been set
    assert await send_cmd(reader, writer, "GET", "k") is None

    # Calling DISCARD or EXEC without MULTI returns error
    err1 = await send_cmd(reader, writer, "DISCARD")
    assert "ERR DISCARD without MULTI" in err1.message

    err2 = await send_cmd(reader, writer, "EXEC")
    assert "ERR EXEC without MULTI" in err2.message

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_transaction_client_isolation(server):
    port = server
    # Two separate clients connecting concurrently
    r1, w1 = await asyncio.open_connection("127.0.0.1", port)
    r2, w2 = await asyncio.open_connection("127.0.0.1", port)

    # Client 1 enters MULTI
    await send_cmd(r1, w1, "MULTI")
    assert (await send_cmd(r1, w1, "SET", "shared", "from_client1")).value == "QUEUED"

    # Client 2 is NOT in MULTI, commands execute immediately!
    assert (await send_cmd(r2, w2, "SET", "shared", "from_client2")).value == "OK"
    assert await send_cmd(r2, w2, "GET", "shared") == b"from_client2"

    # Client 1 finally EXECutes
    await send_cmd(r1, w1, "EXEC")

    # Now shared is updated to client 1's value
    assert await send_cmd(r2, w2, "GET", "shared") == b"from_client1"

    w1.close()
    await w1.wait_closed()
    w2.close()
    await w2.wait_closed()