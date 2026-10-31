from pathlib import Path

from pyredis.commands import execute_command
from pyredis.protocol import INCOMPLETE, parse, serialize
from pyredis.storage import Database

WRITE_COMMANDS = {
    b"SET",
    b"DEL",
    b"EXPIRE",
    b"PERSIST",
    b"LPUSH",
    b"RPUSH",
    b"LPOP",
    b"RPOP",
    b"HSET",
    b"HDEL",
    b"SADD",
    b"SREM",
}


class AOFManager:
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

    def append(self, cmd_name: bytes, args: list[bytes]) -> None:
        if cmd_name.upper() not in WRITE_COMMANDS:
            return

        payload = serialize([cmd_name, *args])
        with open(self.filepath, "ab") as f:
            f.write(payload)
            f.flush()

    def load(self, db: Database) -> int:
        if not self.filepath.exists():
            return 0

        with open(self.filepath, "rb") as f:
            data = f.read()

        pos = 0
        replayed_count = 0
        while pos < len(data):
            result = parse(data, pos)
            if result is INCOMPLETE:
                break

            value, pos = result

            cmd_name = value[0]
            cmd_args = value[1:]
            execute_command(db, cmd_name, cmd_args)
            replayed_count += 1

        return replayed_count
