from typing import Any

from pyredis.protocol import ErrorReply
from pyredis.commands.server import cmd_ping
from pyredis.commands.strings import cmd_get, cmd_set
from pyredis.commands.keys import cmd_del, cmd_exists, cmd_expire, cmd_ttl, cmd_persist
from pyredis.commands.lists import cmd_lpush, cmd_rpush, cmd_lpop, cmd_rpop, cmd_llen, cmd_lrange
from pyredis.commands.hashes import cmd_hset, cmd_hget, cmd_hdel, cmd_hexists, cmd_hlen, cmd_hgetall
from pyredis.commands.sets import cmd_sadd, cmd_smembers, cmd_srem, cmd_sismember, cmd_scard
from pyredis.storage import Database

COMMANDS = {
    b"PING": cmd_ping,
    b"GET": cmd_get,
    b"SET": cmd_set,
    b"DEL": cmd_del,
    b"EXISTS": cmd_exists,
    b"EXPIRE": cmd_expire,
    b"TTL": cmd_ttl,
    b"PERSIST": cmd_persist,
    b"LPUSH": cmd_lpush,
    b"RPUSH": cmd_rpush,
    b"LPOP": cmd_lpop,
    b"RPOP": cmd_rpop,
    b"LLEN": cmd_llen,
    b"LRANGE": cmd_lrange,
    b"HSET": cmd_hset,
    b"HGET": cmd_hget,
    b"HDEL": cmd_hdel,
    b"HEXISTS": cmd_hexists,
    b"HLEN": cmd_hlen,
    b"HGETALL": cmd_hgetall,
    b"SADD": cmd_sadd,
    b"SMEMBERS": cmd_smembers,
    b"SREM": cmd_srem,
    b"SISMEMBER": cmd_sismember,
    b"SCARD": cmd_scard,
}

def execute_command(db: Database, cmd_name: bytes, args: list[bytes]) -> Any:
    handler = COMMANDS.get(cmd_name.upper())
    if handler is None:
        cmd_str = cmd_name.decode("utf-8", errors="replace")
        return ErrorReply(f"ERR unknown command '{cmd_str}'")
    return handler(db, args)