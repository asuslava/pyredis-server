"""Unit tests for Redis List commands."""

from pyredis.commands import execute_command
from pyredis.protocol import ErrorReply
from pyredis.storage import Database


def test_lpush_and_llen():
    db = Database()
    # Pushing single and multiple elements
    assert execute_command(db, b"LPUSH", [b"mylist", b"world"]) == 1
    # LPUSH "hello" goes to the front
    assert execute_command(db, b"LPUSH", [b"mylist", b"hello"]) == 2

    assert execute_command(db, b"LLEN", [b"mylist"]) == 2
    assert execute_command(db, b"LLEN", [b"nonexistent"]) == 0


def test_rpush():
    db = Database()
    assert execute_command(db, b"RPUSH", [b"mylist", b"a", b"b", b"c"]) == 3
    assert execute_command(db, b"LRANGE", [b"mylist", b"0", b"-1"]) == [
        b"a",
        b"b",
        b"c",
    ]


def test_lpop_and_rpop():
    db = Database()
    execute_command(db, b"RPUSH", [b"letters", b"x", b"y", b"z"])

    # LPOP gets the head
    assert execute_command(db, b"LPOP", [b"letters"]) == b"x"
    # RPOP gets the tail
    assert execute_command(db, b"RPOP", [b"letters"]) == b"z"
    # One item remains: 'y'
    assert execute_command(db, b"LPOP", [b"letters"]) == b"y"

    # Now the list is empty -> Key should be auto-deleted
    assert execute_command(db, b"EXISTS", [b"letters"]) == 0
    # Popping from empty/missing key returns None
    assert execute_command(db, b"LPOP", [b"letters"]) is None
    assert execute_command(db, b"RPOP", [b"letters"]) is None


def test_lrange_indexing_and_bounds():
    db = Database()
    execute_command(db, b"RPUSH", [b"nums", b"0", b"1", b"2", b"3", b"4"])

    # Full list
    assert execute_command(db, b"LRANGE", [b"nums", b"0", b"-1"]) == [
        b"0",
        b"1",
        b"2",
        b"3",
        b"4",
    ]
    # Inclusive subslice [1, 3] -> elements 1, 2, 3
    assert execute_command(db, b"LRANGE", [b"nums", b"1", b"3"]) == [
        b"1",
        b"2",
        b"3",
    ]
    # Negative indices
    assert execute_command(db, b"LRANGE", [b"nums", b"-3", b"-1"]) == [
        b"2",
        b"3",
        b"4",
    ]
    # Out of bounds stop -> clamp to end
    assert execute_command(db, b"LRANGE", [b"nums", b"3", b"100"]) == [b"3", b"4"]
    # Start past end -> empty list
    assert execute_command(db, b"LRANGE", [b"nums", b"10", b"20"]) == []
    # Missing key -> empty list
    assert execute_command(db, b"LRANGE", [b"missing", b"0", b"-1"]) == []


def test_list_wrong_type():
    db = Database()
    execute_command(db, b"SET", [b"string_key", b"foo"])

    # LPUSH and RPUSH take 2 args
    for cmd in [b"LPUSH", b"RPUSH"]:
        res = execute_command(db, cmd, [b"string_key", b"v"])
        assert isinstance(res, ErrorReply)
        assert "WRONGTYPE" in res.message

    # LPOP, RPOP, LLEN take 1 arg
    for cmd in [b"LPOP", b"RPOP", b"LLEN"]:
        res = execute_command(db, cmd, [b"string_key"])
        assert isinstance(res, ErrorReply)
        assert "WRONGTYPE" in res.message

    # LRANGE takes 3 args
    res = execute_command(db, b"LRANGE", [b"string_key", b"0", b"-1"])
    assert isinstance(res, ErrorReply)
    assert "WRONGTYPE" in res.message


def test_list_argument_errors():
    db = Database()
    # Too few args
    assert isinstance(execute_command(db, b"LPUSH", [b"k"]), ErrorReply)
    assert isinstance(execute_command(db, b"RPUSH", [b"k"]), ErrorReply)
    assert isinstance(execute_command(db, b"LPOP", []), ErrorReply)
    assert isinstance(execute_command(db, b"LLEN", [b"k", b"extra"]), ErrorReply)
    assert isinstance(
        execute_command(db, b"LRANGE", [b"k", b"not_a_num", b"1"]), ErrorReply
    )