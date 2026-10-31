import asyncio

from pyredis.commands import execute_command
from pyredis.commands.pubsub import cmd_publish, cmd_subscribe, cmd_unsubscribe
from pyredis.commands.transactions import cmd_discard, cmd_exec, cmd_multi
from pyredis.context import ClientContext
from pyredis.expiration import active_expiration_loop
from pyredis.persistence import AOFManager
from pyredis.protocol import (
    ErrorReply,
    Incomplete,
    SimpleString,
    parse,
    serialize,
)
from pyredis.pubsub import PubSubHub
from pyredis.storage import Database


class RedisServer:
    def __init__(
        self,
        db: Database | None = None,
        host: str = "127.0.0.1",
        port: int = 6379,
        aof: AOFManager | None = None,
    ):
        self.db = db if db is not None else Database()
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None
        self.aof = aof
        self.hub = PubSubHub()

    async def start(self) -> None:

        if self.aof is not None:
            count = self.aof.load(self.db)
            if count > 0:
                print(f"Loaded {count} commands from AOF")

        expire_task = asyncio.create_task(active_expiration_loop(self.db))
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )

        try:
            async with self._server:
                await self._server.serve_forever()
        finally:
            expire_task.cancel()
            await asyncio.gather(expire_task, return_exceptions=True)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        buffer = bytearray()
        context = ClientContext()
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer.extend(chunk)

                while True:
                    result = parse(bytes(buffer), 0)
                    if isinstance(result, Incomplete):
                        break
                    value, new_pos = result
                    del buffer[:new_pos]

                    if not isinstance(value, list) or len(value) == 0:
                        continue

                    cmd_name = value[0]
                    cmd_args = value[1:]

                    if cmd_name.upper() == b"QUIT":
                        writer.write(serialize(SimpleString("OK")))
                        await writer.drain()
                        return

                    if cmd_name.upper() == b"SUBSCRIBE":
                        replies = cmd_subscribe(self.hub, writer, cmd_args)
                        if isinstance(replies, ErrorReply):
                            writer.write(serialize(replies))
                        else:
                            for r in replies:
                                writer.write(serialize(r))
                        await writer.drain()
                        continue

                    elif cmd_name.upper() == b"UNSUBSCRIBE":
                        replies = cmd_unsubscribe(self.hub, writer, cmd_args)
                        for r in replies:
                            writer.write(serialize(r))
                        await writer.drain()
                        continue

                    elif cmd_name.upper() == b"MULTI":
                        reply = cmd_multi(context, cmd_args)
                    elif cmd_name.upper() == b"DISCARD":
                        reply = cmd_discard(context, cmd_args)
                    elif cmd_name.upper() == b"EXEC":
                        reply = cmd_exec(self.db, context, self.aof, cmd_args)
                    elif cmd_name.upper() == b"PUBLISH":
                        reply = cmd_publish(self.hub, cmd_args)
                    elif context.in_multi:
                        context.queue.append((cmd_name, cmd_args))
                        reply = SimpleString("QUEUED")
                    else:
                        reply = execute_command(self.db, cmd_name, cmd_args)

                        if self.aof is not None and not isinstance(reply, ErrorReply):
                            self.aof.append(cmd_name, cmd_args)

                    reply_bytes = serialize(reply)

                    writer.write(reply_bytes)
                    await writer.drain()
        finally:
            self.hub.unsubscribe_all(writer)
            writer.close()
            await writer.wait_closed()
