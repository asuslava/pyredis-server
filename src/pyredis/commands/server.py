from typing import Any

from pyredis.protocol import ErrorReply, SimpleString
from pyredis.storage import Database


def cmd_ping(db: Database, args: list[bytes]) -> Any:
    if len(args) == 0:
        return SimpleString("PONG")
    if len(args) == 1:
        return args[0]
    return ErrorReply("ERR wrong number of arguments for 'ping' command")
