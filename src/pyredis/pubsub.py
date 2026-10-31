import asyncio
from collections import defaultdict

from pyredis.protocol import serialize


class PubSubHub:
    def __init__(self) -> None:
        self._channels: dict[bytes, set[asyncio.StreamWriter]] = defaultdict(set)
        self._subscribers: dict[asyncio.StreamWriter, set[bytes]] = defaultdict(set)

    def subscribe(self, channel: bytes, writer: asyncio.StreamWriter) -> int:
        self._channels[channel].add(writer)
        self._subscribers[writer].add(channel)

        return len(self._subscribers[writer])

    def unsubscribe(self, channel: bytes, writer: asyncio.StreamWriter) -> int:
        if channel in self._channels:
            self._channels[channel].discard(writer)
            if len(self._channels[channel]) == 0:
                del self._channels[channel]

        if writer in self._subscribers:
            self._subscribers[writer].discard(channel)
            if len(self._subscribers[writer]) == 0:
                del self._subscribers[writer]

        return len(self._subscribers[writer])

    def unsubscribe_all(self, writer: asyncio.StreamWriter) -> None:
        channels = self._subscribers.pop(writer, set())
        for channel in channels:
            if channel in self._channels:
                self._channels[channel].discard(writer)
                count = len(self._channels[channel])
                if count == 0:
                    del self._channels[channel]

    def publish(self, channel: bytes, message: bytes) -> int:
        writers = self._channels.get(channel, set())

        if not writers:
            return 0

        payload = serialize([b"message", channel, message])

        sub_messaged = 0
        for writer in writers:
            writer.write(payload)
            sub_messaged += 1

        return sub_messaged
