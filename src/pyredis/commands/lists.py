from typing import Any

from pyredis.protocol import ErrorReply
from pyredis.storage import Database, ValueType, WrongTypeError
from collections import deque


def cmd_lpush(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'lpush' command")

    try:
        items = db.get_or_create(key=args[0], expected_type=ValueType.LIST, factory=deque)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    for i in args[1:]:
        items.appendleft(i)

    return len(items)

def cmd_rpush(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'rpush' command")

    try:
        items = db.get_or_create(key=args[0], expected_type=ValueType.LIST, factory=deque)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    for i in args[1:]:
        items.append(i)

    return len(items)

def cmd_lpop(db: Database, args: list[bytes]) -> Any:
    if len(args) < 1:
        return ErrorReply("ERR wrong number of arguments for 'lpop' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.LIST)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None or len(items) == 0:
        return None

    val = items.popleft()

    if len(items) == 0:
        db.delete(args[0])

    return val

def cmd_rpop(db: Database, args: list[bytes]) -> Any:
    if len(args) < 1:
        return ErrorReply("ERR wrong number of arguments for 'rpop' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.LIST)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None or len(items) == 0:
        return None

    val = items.pop()

    if len(items) == 0:
        db.delete(args[0])

    return val

def cmd_llen(db: Database, args: list[bytes]) -> int | ErrorReply | None:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'llen' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.LIST)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return 0

    return len(items)

def cmd_lrange(db: Database, args: list[bytes]) -> Any:
    if len(args) != 3:
        return ErrorReply("ERR wrong number of arguments for 'lrange' command")

    try:
        start = int(args[1])
        end = int(args[2])
    except ValueError:
        return ErrorReply("ERR value is not an integer or out of range")

    try:
        items = db.get(key=args[0], expected_type=ValueType.LIST)
    except WrongTypeError:
        return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")

    if items is None:
        return []

    elements = list(items)
    if start < 0:
        start = max(0, len(elements) + start)
    if end < 0:
        end += len(elements)

    if start >= len(elements) or start > end:
        return []

    return elements[start:min(end+1, len(elements))]

