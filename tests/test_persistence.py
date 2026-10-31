"""Unit tests for AOF persistence."""

from pyredis.commands import execute_command
from pyredis.persistence import AOFManager
from pyredis.storage import Database


def test_aof_append_and_load(tmp_path):
    aof_file = tmp_path / "test.aof"
    aof = AOFManager(aof_file)

    db1 = Database()

    # Simulate client executing write commands
    execute_command(db1, b"SET", [b"name", b"Alice"])
    aof.append(b"SET", [b"name", b"Alice"])

    execute_command(db1, b"LPUSH", [b"tasks", b"task1", b"task2"])
    aof.append(b"LPUSH", [b"tasks", b"task1", b"task2"])

    execute_command(db1, b"HSET", [b"user", b"age", b"25"])
    aof.append(b"HSET", [b"user", b"age", b"25"])

    # Read commands are NOT appended
    aof.append(b"GET", [b"name"])
    aof.append(b"PING", [])

    # Verify AOF file was created and is non-empty
    assert aof_file.exists()
    assert aof_file.stat().st_size > 0

    # Start a FRESH new database (simulating server reboot)
    db2 = Database()
    assert db2.get(b"name") is None

    # Replay commands from AOF into new database
    replayed = aof.load(db2)
    assert replayed == 3  # SET, LPUSH, HSET (GET and PING were ignored)

    # Verify all data was completely restored!
    assert execute_command(db2, b"GET", [b"name"]) == b"Alice"
    assert execute_command(db2, b"LRANGE", [b"tasks", b"0", b"-1"]) == [
        b"task2",
        b"task1",
    ]
    assert execute_command(db2, b"HGET", [b"user", b"age"]) == b"25"


def test_aof_load_nonexistent_file(tmp_path):
    missing_file = tmp_path / "does_not_exist.aof"
    aof = AOFManager(missing_file)
    db = Database()

    # Loading a missing file returns 0 without crashing
    assert aof.load(db) == 0
