import asyncio

from pyredis.commands import execute_command
from pyredis.storage import Database
from pyredis.protocol import parse, INCOMPLETE, serialize, SimpleString


class RedisServer:
    def __init__(self, db: Database | None = None, host: str = "127.0.0.1", port: int = 6379):
        self.db = db if db is not None else Database()
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)

        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        buffer = bytearray()
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer.extend(chunk)

                while True:
                    result = parse(bytes(buffer), 0)
                    if result is INCOMPLETE:
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

                    reply = execute_command(self.db, cmd_name, cmd_args)
                    reply_bytes = serialize(reply)

                    writer.write(reply_bytes)
                    await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

