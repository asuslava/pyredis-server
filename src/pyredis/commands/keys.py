from pyredis.protocol import ErrorReply
from pyredis.storage import Database


def cmd_del(db: Database, args: list[bytes]) -> int | ErrorReply:
    if not args:
        return ErrorReply("ERR wrong number of arguments for 'del' command")
    return db.delete(*args)


def cmd_exists(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'exists' command")
    return 1 if db.exists(args[0]) else 0


def cmd_expire(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 2:
        return ErrorReply("ERR wrong number of arguments for 'expire' command")
    try:
        seconds = float(args[1])
    except ValueError:
        return ErrorReply("ERR value is not an integer or out of range")
    return 1 if db.set_expiry(args[0], db.now() + seconds) else 0


def cmd_persist(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'persist' command")
    return 1 if db.persist(args[0]) else 0


def cmd_ttl(db: Database, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 1:
        return ErrorReply("ERR wrong number of arguments for 'ttl' command")
    if not db.exists(args[0]):
        return -2
    if db.get_expiry(args[0]) is None:
        return -1
    return max(0, int(db.get_expiry(args[0]) - db.now()))
