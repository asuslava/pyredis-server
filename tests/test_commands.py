"""Tests for the commands package and execute_command router."""

import pytest
from pyredis.commands import execute_command
from pyredis.protocol import ErrorReply, SimpleString
from pyredis.storage import Database, ValueType


@pytest.fixture
def db():
    # Use a fixed mock clock so TTL/expiry tests are deterministic
    current_time = 1000.0

    def mock_clock():
        return current_time

    database = Database(clock=mock_clock)
    # Attach clock controller to db so tests can advance time
    database._set_time = lambda t: nonlocal_set_time(t)

    def nonlocal_set_time(new_time):
        nonlocal current_time
        current_time = new_time

    return database


# ─── Unknown Command ─────────────────────────────────────────────────────────


def test_unknown_command(db):
    res = execute_command(db, b"FOOBAR", [])
    assert isinstance(res, ErrorReply)
    assert "unknown command" in res.message.lower()


def test_case_insensitive_dispatch(db):
    # 'ping', 'Ping', 'PING' should all work
    res = execute_command(db, b"ping", [])
    assert res == SimpleString("PONG")


# ─── PING (commands/server.py) ───────────────────────────────────────────────


def test_ping_no_args(db):
    assert execute_command(db, b"PING", []) == SimpleString("PONG")


def test_ping_with_message(db):
    assert execute_command(db, b"PING", [b"hello"]) == b"hello"


def test_ping_too_many_args(db):
    res = execute_command(db, b"PING", [b"a", b"b"])
    assert isinstance(res, ErrorReply)
    assert "wrong number of arguments" in res.message.lower()


# ─── GET / SET (commands/strings.py) ─────────────────────────────────────────


def test_set_and_get(db):
    set_res = execute_command(db, b"SET", [b"user", b"Alice"])
    assert set_res == SimpleString("OK")

    get_res = execute_command(db, b"GET", [b"user"])
    assert get_res == b"Alice"


def test_get_nonexistent_key(db):
    # Missing key returns None (which serialize turns into $-1\r\n)
    assert execute_command(db, b"GET", [b"nonexistent"]) is None


def test_get_wrong_type(db):
    # Storing a list, then trying to GET it should return WRONGTYPE error
    db.set(b"mylist", [1, 2], ValueType.LIST)
    res = execute_command(db, b"GET", [b"mylist"])
    assert isinstance(res, ErrorReply)
    assert "WRONGTYPE" in res.message


def test_set_wrong_args(db):
    res = execute_command(db, b"SET", [b"only_key"])
    assert isinstance(res, ErrorReply)
    assert "wrong number of arguments" in res.message.lower()


def test_get_wrong_args(db):
    res = execute_command(db, b"GET", [b"k1", b"k2"])
    assert isinstance(res, ErrorReply)
    assert "wrong number of arguments" in res.message.lower()


# ─── DEL / EXISTS (commands/keys.py) ─────────────────────────────────────────


def test_del_existing_and_missing(db):
    execute_command(db, b"SET", [b"k1", b"v1"])
    execute_command(db, b"SET", [b"k2", b"v2"])

    # Deleting k1, k2 and a missing key -> should return 2
    deleted = execute_command(db, b"DEL", [b"k1", b"k2", b"missing"])
    assert deleted == 2

    # Verify they are gone
    assert execute_command(db, b"GET", [b"k1"]) is None


def test_del_no_args(db):
    res = execute_command(db, b"DEL", [])
    assert isinstance(res, ErrorReply)


def test_exists(db):
    execute_command(db, b"SET", [b"k", b"v"])
    assert execute_command(db, b"EXISTS", [b"k"]) == 1
    assert execute_command(db, b"EXISTS", [b"missing"]) == 0


# ─── EXPIRE / TTL / PERSIST (commands/keys.py) ───────────────────────────────


def test_ttl_on_missing_key(db):
    # Redis spec: returns -2 if key does not exist
    assert execute_command(db, b"TTL", [b"missing"]) == -2


def test_ttl_on_permanent_key(db):
    # Redis spec: returns -1 if key exists with no expiry
    execute_command(db, b"SET", [b"perm", b"val"])
    assert execute_command(db, b"TTL", [b"perm"]) == -1


def test_expire_and_ttl(db):
    execute_command(db, b"SET", [b"temp", b"val"])

    # Set expiry for 60 seconds
    expire_res = execute_command(db, b"EXPIRE", [b"temp", b"60"])
    assert expire_res == 1

    # Check TTL immediately
    assert execute_command(db, b"TTL", [b"temp"]) == 60

    # Advance clock by 20 seconds -> TTL should be 40
    db._set_time(1020.0)
    assert execute_command(db, b"TTL", [b"temp"]) == 40

    # Advance clock past expiration -> Key is expired (TTL is -2, GET is None)
    db._set_time(1061.0)
    assert execute_command(db, b"TTL", [b"temp"]) == -2
    assert execute_command(db, b"GET", [b"temp"]) is None


def test_expire_invalid_seconds(db):
    execute_command(db, b"SET", [b"k", b"v"])
    res = execute_command(db, b"EXPIRE", [b"k", b"not_a_number"])
    assert isinstance(res, ErrorReply)


def test_persist(db):
    execute_command(db, b"SET", [b"k", b"v"])
    execute_command(db, b"EXPIRE", [b"k", b"100"])

    # Persist removes the expiry -> returns 1
    assert execute_command(db, b"PERSIST", [b"k"]) == 1
    assert execute_command(db, b"TTL", [b"k"]) == -1

    # Persisting a permanent or missing key -> returns 0
    assert execute_command(db, b"PERSIST", [b"k"]) == 0
    assert execute_command(db, b"PERSIST", [b"missing"]) == 0