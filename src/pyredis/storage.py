import time


class Database:
    def __init__(self):
        self._data = {}
        self._types = {}
        self._expiry = {}

    def set_string(self, key: bytes, value: bytes) -> None:
        self._data[key] = value
        self._types[key] = "string"
        self._expiry.pop(key, None)

    def get_string(self, key: bytes) -> bytes | None:
        if self._is_expired(key):
            return None
        if key in self._data and self._types.get(key) != "string":
            return None
        return self._data.get(key)

    def exists(self, key: bytes) -> bool:
        if self._is_expired(key):
            return False
        return key in self._data

    def delete(self, *keys: bytes) -> int:
        count = 0
        for key in keys:
            if key not in self._data:
                continue
            if self._is_expired(key):
                continue
            if self._delete_key(key):
                count += 1
        return count

    def _delete_key(self, key: bytes) -> bool:
        existed = key in self._data
        self._data.pop(key, None)
        self._types.pop(key, None)
        self._expiry.pop(key, None)
        return existed

    def _is_expired(self, key: bytes) -> bool:
        exp = self._expiry.get(key)
        if exp is None:
            return False
        if time.time() >= exp:
            self._delete_key(key)
            return True
        return False