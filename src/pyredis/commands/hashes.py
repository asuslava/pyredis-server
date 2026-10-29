from typing import Any

from pyredis.protocol import ErrorReply
from pyredis.storage import Database, ValueType, WrongTypeError


def cmd_hset(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 3 or (len(args) - 1) % 2 != 0:
        return ErrorReply("ERR wrong number of arguments for 'hset' command")

    try:
        items = db.get_or_create(key=args[0], expected_type=ValueType.HASH, factory=dict)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    added_count = 0
    for i in range(1, len(args), 2):
        field = args[i]
        value = args[i + 1]
        if field not in items:
            added_count += 1
        items[field] = value

    return added_count

def cmd_hget(db: Database, args: list[bytes]) -> bytes | ErrorReply:
    if len(args) != 2:
        return ErrorReply("ERR wrong number of arguments for 'hget' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.HASH)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return None

    return items.get(args[1])

def cmd_hdel(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'hdel' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.HASH)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return 0

    deleted_count = 0
    for i in args[1:]:
        if items.pop(i, None) is not None:
            deleted_count += 1

    if len(items) == 0:
        db.delete(args[0])

    return deleted_count

def cmd_hexists(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'hexists' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.HASH)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return 0

    return 1 if args[1] in items else 0

def cmd_hlen(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'hlen' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.HASH)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    return len(items) if items is not None else 0

def cmd_hgetall(db: Database, args: list[bytes]) -> list | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'hgetall' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.HASH)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return []

    result = []
    for field, value in items.items():
        result.append(field)
        result.append(value)

    return result