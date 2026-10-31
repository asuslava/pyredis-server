import asyncio

from pyredis.protocol import ErrorReply
from pyredis.pubsub import PubSubHub


def cmd_publish(hub: PubSubHub, args: list[bytes]) -> int | ErrorReply:
    if len(args) != 2:
        return ErrorReply("ERR wrong number of arguments for 'publish' command")

    count = hub.publish(args[0], args[1])
    return count

def cmd_subscribe(hub: PubSubHub, writer: asyncio.StreamWriter, args: list[bytes]) -> list[bytes] | ErrorReply:
    if len(args) < 1:
        return ErrorReply("ERR wrong number of arguments for 'subscribe' command")

    replies = []
    for channel in args:
        count = hub.subscribe(channel, writer)
        replies.append([b"subscribe", channel, count])

    return replies

def cmd_unsubscribe(hub: PubSubHub, writer: asyncio.StreamWriter, args: list[bytes]) -> list[bytes] | ErrorReply:
    channels = list(args) if len(args) > 0 else list(hub._subscribers.get(writer, set()))

    replies = []
    for channel in channels:
        remaining_count = hub.unsubscribe(channel, writer)
        replies.append([b"unsubscribe", channel, remaining_count])

    return replies