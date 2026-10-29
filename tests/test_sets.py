"""Unit tests for Redis Set commands."""

from pyredis.commands import execute_command
from pyredis.protocol import ErrorReply
from pyredis.storage import Database


def test_sadd_and_scard():
    db = Database()
    # Adding multiple new members -> returns count of newly added (3)
    assert execute_command(db, b"SADD", [b"myset", b"a", b"b", b"c"]) == 3
    assert execute_command(db, b"SCARD", [b"myset"]) == 3

    # Adding duplicates -> only new members count
    assert execute_command(db, b"SADD", [b"myset", b"c", b"d"]) == 1
    assert execute_command(db, b"SCARD", [b"myset"]) == 4

    # SCARD on non-existent key returns 0
    assert execute_command(db, b"SCARD", [b"missing"]) == 0


def test_smembers():
    db = Database()
    # Missing key returns empty list
    assert execute_command(db, b"SMEMBERS", [b"missing"]) == []

    execute_command(db, b"SADD", [b"colors", b"red", b"blue", b"green"])
    members = execute_command(db, b"SMEMBERS", [b"colors"])

    # Returns a list, compare as a set because order doesn't matter
    assert isinstance(members, list)
    assert set(members) == {b"red", b"blue", b"green"}


def test_sismember():
    db = Database()
    execute_command(db, b"SADD", [b"fruits", b"apple", b"banana"])

    assert execute_command(db, b"SISMEMBER", [b"fruits", b"apple"]) == 1
    assert execute_command(db, b"SISMEMBER", [b"fruits", b"orange"]) == 0
    # Missing key returns 0
    assert execute_command(db, b"SISMEMBER", [b"missing", b"apple"]) == 0


def test_srem_and_auto_delete():
    db = Database()
    execute_command(db, b"SADD", [b"tags", b"python", b"redis", b"db"])

    # Removing 1 existing and 1 non-existent member -> returns 1
    assert execute_command(db, b"SREM", [b"tags", b"redis", b"rust"]) == 1
    assert execute_command(db, b"SCARD", [b"tags"]) == 2

    # Removing the remaining members -> auto-deletes the key
    assert execute_command(db, b"SREM", [b"tags", b"python", b"db"]) == 2
    assert execute_command(db, b"EXISTS", [b"tags"]) == 0

    # SREM on non-existent key returns 0
    assert execute_command(db, b"SREM", [b"missing", b"item"]) == 0


def test_set_wrong_type():
    db = Database()
    execute_command(db, b"SET", [b"str_key", b"hello"])

    for cmd, args in [
        (b"SADD", [b"str_key", b"m1"]),
        (b"SMEMBERS", [b"str_key"]),
        (b"SREM", [b"str_key", b"m1"]),
        (b"SISMEMBER", [b"str_key", b"m1"]),
        (b"SCARD", [b"str_key"]),
    ]:
        res = execute_command(db, cmd, args)
        assert isinstance(res, ErrorReply)
        assert "WRONGTYPE" in res.message


def test_set_argument_errors():
    db = Database()
    # Too few args
    assert isinstance(execute_command(db, b"SADD", [b"s"]), ErrorReply)
    assert isinstance(execute_command(db, b"SREM", [b"s"]), ErrorReply)
    assert isinstance(execute_command(db, b"SISMEMBER", [b"s"]), ErrorReply)

    # Extra args
    assert isinstance(execute_command(db, b"SMEMBERS", [b"s", b"extra"]), ErrorReply)
    assert isinstance(execute_command(db, b"SCARD", [b"s", b"extra"]), ErrorReply)
    assert isinstance(execute_command(db, b"SISMEMBER", [b"s", b"m", b"extra"]), ErrorReply)