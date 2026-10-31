"""Unit tests for Redis Sorted Set (ZSET) commands."""

from pyredis.commands import execute_command
from pyredis.protocol import ErrorReply
from pyredis.storage import Database


def test_zadd_and_zscore():
    db = Database()
    # Adding two members -> returns 2
    assert (
        execute_command(db, b"ZADD", [b"scores", b"100", b"Alice", b"85.5", b"Bob"])
        == 2
    )

    # Querying their scores
    assert execute_command(db, b"ZSCORE", [b"scores", b"Alice"]) == b"100"
    assert execute_command(db, b"ZSCORE", [b"scores", b"Bob"]) == b"85.5"

    # Updating an existing member's score -> returns 0 (no new member added)
    assert execute_command(db, b"ZADD", [b"scores", b"95", b"Bob"]) == 0
    assert execute_command(db, b"ZSCORE", [b"scores", b"Bob"]) == b"95"

    # Missing member or missing key returns None
    assert execute_command(db, b"ZSCORE", [b"scores", b"Charlie"]) is None
    assert execute_command(db, b"ZSCORE", [b"missing", b"Alice"]) is None


def test_zcard():
    db = Database()
    assert execute_command(db, b"ZCARD", [b"missing"]) == 0

    execute_command(db, b"ZADD", [b"board", b"10", b"a", b"20", b"b", b"30", b"c"])
    assert execute_command(db, b"ZCARD", [b"board"]) == 3


def test_zrem_and_auto_delete():
    db = Database()
    execute_command(db, b"ZADD", [b"board", b"10", b"a", b"20", b"b", b"30", b"c"])

    # Removing 1 existing and 1 non-existent member -> returns 1
    assert execute_command(db, b"ZREM", [b"board", b"a", b"nonexistent"]) == 1
    assert execute_command(db, b"ZCARD", [b"board"]) == 2

    # Removing remaining members -> auto-deletes the key
    assert execute_command(db, b"ZREM", [b"board", b"b", b"c"]) == 2
    assert execute_command(db, b"EXISTS", [b"board"]) == 0
    assert execute_command(db, b"ZREM", [b"missing", b"a"]) == 0


def test_zrange_sorted_by_score():
    db = Database()
    # Add out of order: Bob (200), Charlie (50), Alice (100)
    execute_command(
        db,
        b"ZADD",
        [b"players", b"200", b"Bob", b"50", b"Charlie", b"100", b"Alice"],
    )

    # ZRANGE must return ascending by score: Charlie (50), Alice (100), Bob (200)
    assert execute_command(db, b"ZRANGE", [b"players", b"0", b"-1"]) == [
        b"Charlie",
        b"Alice",
        b"Bob",
    ]

    # Subslice with positive indices
    assert execute_command(db, b"ZRANGE", [b"players", b"0", b"1"]) == [
        b"Charlie",
        b"Alice",
    ]

    # Negative indices
    assert execute_command(db, b"ZRANGE", [b"players", b"-2", b"-1"]) == [
        b"Alice",
        b"Bob",
    ]


def test_zrange_withscores():
    db = Database()
    execute_command(
        db,
        b"ZADD",
        [b"rank", b"10.5", b"player1", b"20", b"player2"],
    )

    # WITHSCORES returns alternating [member, score_bytes, ...]
    assert execute_command(db, b"ZRANGE", [b"rank", b"0", b"-1", b"WITHSCORES"]) == [
        b"player1",
        b"10.5",
        b"player2",
        b"20",
    ]


def test_zrange_missing_and_empty():
    db = Database()
    assert execute_command(db, b"ZRANGE", [b"missing", b"0", b"-1"]) == []


def test_zset_wrong_type():
    db = Database()
    execute_command(db, b"SET", [b"str_key", b"hello"])

    for cmd, args in [
        (b"ZADD", [b"str_key", b"10", b"m"]),
        (b"ZSCORE", [b"str_key", b"m"]),
        (b"ZCARD", [b"str_key"]),
        (b"ZREM", [b"str_key", b"m"]),
        (b"ZRANGE", [b"str_key", b"0", b"-1"]),
    ]:
        res = execute_command(db, cmd, args)
        assert isinstance(res, ErrorReply)
        assert "WRONGTYPE" in res.message


def test_zset_syntax_and_errors():
    db = Database()
    # ZADD requires odd number of total args (key + at least 1 pair)
    assert isinstance(execute_command(db, b"ZADD", [b"z", b"10"]), ErrorReply)
    # ZADD with invalid float score
    assert isinstance(
        execute_command(db, b"ZADD", [b"z", b"not_a_float", b"m"]), ErrorReply
    )

    # ZRANGE with invalid syntax or bad integers
    assert isinstance(
        execute_command(db, b"ZRANGE", [b"z", b"0", b"1", b"BADOPTION"]), ErrorReply
    )
    assert isinstance(execute_command(db, b"ZRANGE", [b"z", b"bad", b"1"]), ErrorReply)
