"""Unit tests for Redis Hash commands."""

from pyredis.commands import execute_command
from pyredis.protocol import ErrorReply
from pyredis.storage import Database


def test_hset_and_hget():
    db = Database()
    # Inserting 2 new fields -> returns 2
    assert execute_command(db, b"HSET", [b"user:1", b"name", b"Alice", b"age", b"30"]) == 2

    # Reading them back
    assert execute_command(db, b"HGET", [b"user:1", b"name"]) == b"Alice"
    assert execute_command(db, b"HGET", [b"user:1", b"age"]) == b"30"

    # Updating an existing field -> returns 0 (no new fields added)
    assert execute_command(db, b"HSET", [b"user:1", b"name", b"Bob"]) == 0
    assert execute_command(db, b"HGET", [b"user:1", b"name"]) == b"Bob"

    # Non-existent field / key
    assert execute_command(db, b"HGET", [b"user:1", b"missing"]) is None
    assert execute_command(db, b"HGET", [b"missing_key", b"field"]) is None


def test_hdel_and_auto_delete():
    db = Database()
    execute_command(db, b"HSET", [b"h", b"f1", b"v1", b"f2", b"v2"])

    # Deleting 1 existing field and 1 non-existent field -> returns 1
    assert execute_command(db, b"HDEL", [b"h", b"f1", b"missing"]) == 1
    assert execute_command(db, b"HGET", [b"h", b"f1"]) is None

    # Deleting the last field -> auto-deletes the key
    assert execute_command(db, b"HDEL", [b"h", b"f2"]) == 1
    assert execute_command(db, b"EXISTS", [b"h"]) == 0

    # HDEL on non-existent key returns 0
    assert execute_command(db, b"HDEL", [b"missing_key", b"f1"]) == 0


def test_hexists_and_hlen():
    db = Database()
    assert execute_command(db, b"HLEN", [b"h"]) == 0
    assert execute_command(db, b"HEXISTS", [b"h", b"f1"]) == 0

    execute_command(db, b"HSET", [b"h", b"f1", b"v1", b"f2", b"v2"])
    assert execute_command(db, b"HLEN", [b"h"]) == 2
    assert execute_command(db, b"HEXISTS", [b"h", b"f1"]) == 1
    assert execute_command(db, b"HEXISTS", [b"h", b"f99"]) == 0


def test_hgetall():
    db = Database()
    # Missing key returns empty list
    assert execute_command(db, b"HGETALL", [b"missing"]) == []

    execute_command(db, b"HSET", [b"h", b"a", b"1", b"b", b"2"])
    res = execute_command(db, b"HGETALL", [b"h"])

    # Flattened alternating pairs: [b"a", b"1", b"b", b"2"]
    assert len(res) == 4
    # Check pair mapping
    as_dict = dict(zip(res[0::2], res[1::2]))
    assert as_dict == {b"a": b"1", b"b": b"2"}


def test_hash_wrong_type():
    db = Database()
    execute_command(db, b"SET", [b"str_key", b"val"])

    for cmd, args in [
        (b"HSET", [b"str_key", b"f", b"v"]),
        (b"HGET", [b"str_key", b"f"]),
        (b"HDEL", [b"str_key", b"f"]),
        (b"HEXISTS", [b"str_key", b"f"]),
        (b"HLEN", [b"str_key"]),
        (b"HGETALL", [b"str_key"]),
    ]:
        res = execute_command(db, cmd, args)
        assert isinstance(res, ErrorReply)
        assert "WRONGTYPE" in res.message


def test_hash_argument_errors():
    db = Database()
    # HSET requires odd number of total args (key + at least 1 pair)
    assert isinstance(execute_command(db, b"HSET", [b"h", b"f1"]), ErrorReply)
    assert isinstance(execute_command(db, b"HSET", [b"h", b"f1", b"v1", b"f2"]), ErrorReply)

    # Wrong arg counts
    assert isinstance(execute_command(db, b"HGET", [b"h"]), ErrorReply)
    assert isinstance(execute_command(db, b"HGET", [b"h", b"f", b"extra"]), ErrorReply)
    assert isinstance(execute_command(db, b"HDEL", [b"h"]), ErrorReply)
    assert isinstance(execute_command(db, b"HEXISTS", [b"h"]), ErrorReply)
    assert isinstance(execute_command(db, b"HLEN", [b"h", b"extra"]), ErrorReply)
    assert isinstance(execute_command(db, b"HGETALL", [b"h", b"extra"]), ErrorReply)