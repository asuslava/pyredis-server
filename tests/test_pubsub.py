"""Integration tests for Redis Pub/Sub."""

import asyncio
import pytest
from pyredis.protocol import parse, serialize
from pyredis.server import RedisServer


@pytest.fixture
async def server():
    srv = RedisServer(host="127.0.0.1", port=0)
    server_task = asyncio.create_task(srv.start())

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


async def read_resp(reader):
    buf = bytearray()
    while True:
        chunk = await reader.read(4096)
        buf.extend(chunk)
        res = parse(bytes(buf), 0)
        if res is not None and getattr(res, "__class__", None).__name__ != "Incomplete":
            val, _ = res
            return val


@pytest.mark.asyncio
async def test_publish_no_subscribers(server):
    port = server
    r, w = await asyncio.open_connection("127.0.0.1", port)

    # Publishing to empty channel returns 0
    count = await send_cmd(r, w, "PUBLISH", "chat", "hello")
    assert count == 0

    w.close()
    await w.wait_closed()


@pytest.mark.asyncio
async def test_subscribe_and_publish(server):
    port = server
    sub_r, sub_w = await asyncio.open_connection("127.0.0.1", port)
    pub_r, pub_w = await asyncio.open_connection("127.0.0.1", port)

    # 1. Subscriber subscribes to "news"
    sub_w.write(serialize([b"SUBSCRIBE", b"news"]))
    await sub_w.drain()

    # Read confirmation: ["subscribe", b"news", 1]
    confirm = await read_resp(sub_r)
    assert confirm == [b"subscribe", b"news", 1]

    # 2. Publisher publishes to "news" -> returns 1
    count = await send_cmd(pub_r, pub_w, "PUBLISH", "news", "breaking news!")
    assert count == 1

    # 3. Subscriber receives the live message!
    msg = await read_resp(sub_r)
    assert msg == [b"message", b"news", b"breaking news!"]

    sub_w.close()
    await sub_w.wait_closed()
    pub_w.close()
    await pub_w.wait_closed()


@pytest.mark.asyncio
async def test_multiple_subscribers_broadcast(server):
    port = server
    s1_r, s1_w = await asyncio.open_connection("127.0.0.1", port)
    s2_r, s2_w = await asyncio.open_connection("127.0.0.1", port)
    pub_r, pub_w = await asyncio.open_connection("127.0.0.1", port)

    # Both subscribe to "sports"
    s1_w.write(serialize([b"SUBSCRIBE", b"sports"]))
    await s1_w.drain()
    await read_resp(s1_r)

    s2_w.write(serialize([b"SUBSCRIBE", b"sports"]))
    await s2_w.drain()
    await read_resp(s2_r)

    # Publisher publishes -> returns 2
    count = await send_cmd(pub_r, pub_w, "PUBLISH", "sports", "Goal!")
    assert count == 2

    # Both receive the exact same message
    msg1 = await read_resp(s1_r)
    msg2 = await read_resp(s2_r)
    assert msg1 == [b"message", b"sports", b"Goal!"]
    assert msg2 == [b"message", b"sports", b"Goal!"]

    s1_w.close()
    await s1_w.wait_closed()
    s2_w.close()
    await s2_w.wait_closed()
    pub_w.close()
    await pub_w.wait_closed()


@pytest.mark.asyncio
async def test_unsubscribe(server):
    port = server
    sub_r, sub_w = await asyncio.open_connection("127.0.0.1", port)
    pub_r, pub_w = await asyncio.open_connection("127.0.0.1", port)

    # Subscribe to "c1"
    sub_w.write(serialize([b"SUBSCRIBE", b"c1"]))
    await sub_w.drain()
    await read_resp(sub_r)

    # Unsubscribe from "c1"
    sub_w.write(serialize([b"UNSUBSCRIBE", b"c1"]))
    await sub_w.drain()
    unsub_reply = await read_resp(sub_r)
    assert unsub_reply == [b"unsubscribe", b"c1", 0]

    # Publishing to "c1" now reaches 0 subscribers
    count = await send_cmd(pub_r, pub_w, "PUBLISH", "c1", "test")
    assert count == 0

    sub_w.close()
    await sub_w.wait_closed()
    pub_w.close()
    await pub_w.wait_closed()