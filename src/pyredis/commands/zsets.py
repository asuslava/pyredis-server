from typing import Any

from pyredis.protocol import ErrorReply
from pyredis.storage import Database, ValueType, WrongTypeError


def cmd_zadd(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 3 or (len(args) - 1) % 2 != 0:
        return ErrorReply("ERR wrong number of arguments for 'zadd' command")

    try:
        items = db.get_or_create(
            key=args[0], expected_type=ValueType.ZSET, factory=dict
        )
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    count = 0
    for i in range(1, len(args), 2):
        try:
            score = float(args[i])
        except ValueError:
            return ErrorReply("ERR value is not a valid float")

        member = args[i + 1]
        if member not in items:
            count += 1
        items[member] = score

    return count


def cmd_zscore(db: Database, args: list[bytes]) -> Any:
    if len(args) != 2:
        return ErrorReply("ERR wrong number of arguments for 'zscore' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.ZSET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None or args[1] not in items:
        return None

    score = items[args[1]]

    if score.is_integer():
        return str(int(score)).encode()
    return str(score).encode()


def cmd_zrem(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) < 2:
        return ErrorReply("ERR wrong number of arguments for 'zrem' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.ZSET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return 0

    remove_count = 0
    for i in args[1:]:
        if i in items and items.pop(i, None) is not None:
            remove_count += 1

    if len(items) == 0:
        db.delete(args[0])

    return remove_count


def cmd_zcard(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'zcard' command")

    try:
        items = db.get(key=args[0], expected_type=ValueType.ZSET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return 0

    return len(items)


def cmd_zrange(db: Database, args: list[bytes]) -> list[bytes] | ErrorReply:
    if len(args) not in (3, 4):
        return ErrorReply("ERR wrong number of arguments for 'zrange' command")

    if len(args) == 4 and args[3].upper() != b"WITHSCORES":
        return ErrorReply("ERR syntax error")

    try:
        start = int(args[1])
        stop = int(args[2])
    except ValueError:
        return ErrorReply("ERR value is not an integer or out of range")

    try:
        items = db.get(key=args[0], expected_type=ValueType.ZSET)
    except WrongTypeError:
        return ErrorReply(
            "WRONGTYPE Operation against a key holding the wrong kind of value"
        )

    if items is None:
        return []

    sorted_pairs = sorted(items.items(), key=lambda x: (x[1], x[0]))
    if start < 0:
        start = max(0, len(sorted_pairs) + start)
    if stop < 0:
        stop = len(sorted_pairs) + stop

    if start >= len(sorted_pairs) or start > stop:
        return []

    sliced = sorted_pairs[start : min(stop + 1, len(args))]

    with_scores = len(args) == 4
    if not with_scores:
        return [member for member, score in sliced]

    result = []
    for member, score in sliced:
        result.append(member)
        score_bytes = (
            str(int(score)).encode() if score.is_integer() else str(score).encode()
        )
        result.append(score_bytes)

    return result
