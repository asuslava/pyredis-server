from pyredis.protocol import ErrorReply
from pyredis.storage import Database, ValueType, WrongTypeError


def cmd_sadd(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'sadd' command")

    try:
        items = db.get_or_create(key=args[0], expected_type=ValueType.SET, factory=set)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    added_count = 0
    for i in args[1:]:
        if i not in items:
            added_count += 1
        items.add(i)

    return added_count


def cmd_smembers(db: Database, args: list[bytes]) -> list | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'smembers' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.SET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return []

    return list(items)


def cmd_srem(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'srem' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.SET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return 0

    remove_count = 0
    for i in args[1:]:
        if i in items:
            items.discard(i)
            remove_count += 1

    if len(items) == 0:
        db.delete(args[0])

    return remove_count


def cmd_sismember(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 2:
        return ErrorReply("ERR wrong number of arguments for 'sismember' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.SET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return 0

    return 1 if args[1] in items else 0


def cmd_scard(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'scard' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.SET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return 0

    return len(items)
