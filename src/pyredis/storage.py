import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValueType(str, Enum):
    STRING = "string"
    LIST = "list"
    SET = "set"
    HASH = "hash"
    ZSET = "zset"


class WrongTypeError(Exception):
    pass


@dataclass(slots=True)
class Entry:
    value: Any
    type: ValueType
    expiry: float | None = None


class Database:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._entries: dict[bytes, Entry] = {}
        self._clock = clock

    def _live_entry(self, key: bytes) -> Entry | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.expiry is not None and self._clock() >= entry.expiry:
            self._entries.pop(key)
            return None

        return entry

    def get(self, key: bytes, expected_type: ValueType | None = None) -> Any | None:
        entry = self._live_entry(key)
        if entry is None:
            return None

        if expected_type is not None and entry.type != expected_type:
            raise WrongTypeError(
                "WRONGTYPE Operation against a key holding the wrong kind of value"
            )

        return entry.value

    def set(
        self, key: bytes, value: Any, value_type: ValueType, expiry: float | None = None
    ):
        self._entries[key] = Entry(value, value_type, expiry)

    def get_or_create(
        self, key: bytes, expected_type: ValueType, factory: Callable[[], Any]
    ) -> Any:
        value = self.get(key, expected_type)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, expected_type)
        return value

    def exists(self, key: bytes) -> bool:
        return self._live_entry(key) is not None

    def delete(self, *keys: bytes) -> int:
        count = 0
        for key in keys:
            entry = self._live_entry(key)
            if entry is not None:
                self._entries.pop(key)
                count += 1
        return count

    def type_of(self, key: bytes) -> str:
        entry = self._live_entry(key)
        if entry is None:
            return "none"
        return entry.type.value

    def keys(self) -> list[bytes]:
        res = []

        for key in list(self._entries):
            entry = self._live_entry(key)
            if entry is not None:
                res.append(key)
        return res

    def flush(self) -> None:
        self._entries.clear()

    def set_expiry(self, key: bytes, when: float) -> bool:
        entry = self._live_entry(key)
        if entry is None:
            return False

        entry.expiry = when
        return True

    def get_expiry(self, key: bytes) -> float | None:
        entry = self._live_entry(key)
        if entry is None:
            return None
        return entry.expiry

    def persist(self, key: bytes) -> bool:
        entry = self._live_entry(key)
        if entry is None or entry.expiry is None:
            return False

        entry.expiry = None
        return True

    def now(self) -> float:
        return self._clock()

    def active_expire_cycle(self, sample_size: int = 20) -> tuple[int, int]:
        expiring_keys = [
            key for key, entry in self._entries.items() if entry.expiry is not None
        ]

        if not expiring_keys:
            return (0, 0)

        num_to_sample = min(len(expiring_keys), sample_size)
        sample_keys = random.sample(expiring_keys, num_to_sample)

        expired_count = 0
        for key in sample_keys:
            if self._live_entry(key) is None:
                expired_count += 1

        return (len(sample_keys), expired_count)
