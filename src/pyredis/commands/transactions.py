from typing import Any

from pyredis.commands import execute_command
from pyredis.context import ClientContext
from pyredis.protocol import ErrorReply, SimpleString
from pyredis.storage import Database


def cmd_multi(context: ClientContext, args: list[bytes]) -> Any:
    if len(args) != 0:
        return ErrorReply("ERR wrong number of arguments for 'multi' command")
    if context.in_multi:
        return ErrorReply("ERR MULTI calls can not be nested")

    context.in_multi = True
    context.queue.clear()

    return SimpleString("OK")

def cmd_discard(context: ClientContext, args: list[bytes]) -> Any:
    if len(args) != 0:
        return ErrorReply("ERR wrong number of arguments for 'discard' command")
    if not context.in_multi:
        return ErrorReply("ERR DISCARD without MULTI")

    context.reset_multi()
    return SimpleString("OK")

def cmd_exec(db: Database, context: ClientContext, aof: Any, args: list[bytes]) -> Any:
    if len(args) != 0:
        return ErrorReply("ERR wrong number of arguments for 'exec' command")
    if not context.in_multi:
        return ErrorReply("ERR EXEC without MULTI")

    commands = list(context.queue)
    context.reset_multi()

    results = []
    for cmd_name, cmd_args in commands:
        res = execute_command(db, cmd_name, cmd_args)

        if aof is not None and not isinstance(res, ErrorReply):
            aof.append(cmd_name, cmd_args)

        results.append(res)

    return results

