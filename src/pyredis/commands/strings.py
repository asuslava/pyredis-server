from typing import Any

from pyredis.protocol import ErrorReply, SimpleString
from pyredis.storage import Database, ValueType, WrongTypeError


def cmd_get(db: Database, args: list[bytes]) -> Any:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'get' command")
    try:
        return db.get(args[0], ValueType.STRING)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

def cmd_set(db: Database, args: list[bytes]) -> ErrorReply | SimpleString:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'set' command")
    db.set(args[0], args[1], ValueType.STRING)
    return SimpleString("OK")