import pytest

from pyredis.storage import Database, ValueType, WrongTypeError


class FakeClock:
    def __init__(self, now: float = 0.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def make_db(now: float = 0.0):
    clock = FakeClock(now)
    return Database(clock=clock), clock


# ---------- exists ----------


def test_exists_present_key():
    db, _ = make_db()
    db.set(b"k", b"v", ValueType.STRING)
    assert db.exists(b"k") is True


def test_exists_missing_key():
    db, _ = make_db()
    assert db.exists(b"k") is False


def test_exists_works_for_any_type():
    db, _ = make_db()
    db.set(b"l", [b"a"], ValueType.LIST)
    db.set(b"s", {b"a"}, ValueType.SET)
    assert db.exists(b"l") is True
    assert db.exists(b"s") is True


def test_exists_expired_key_before_expiry():
    db, _clock = make_db(now=99.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.exists(b"k") is True


def test_exists_expired_key_at_expiry():
    db, _clock = make_db(now=100.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.exists(b"k") is False
    assert b"k" not in db._entries


def test_exists_expired_key_after_expiry():
    db, _clock = make_db(now=150.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.exists(b"k") is False


# ---------- delete ----------


def test_delete_one_existing_key():
    db, _ = make_db()
    db.set(b"k", b"v", ValueType.STRING)
    assert db.delete(b"k") == 1
    assert db.get(b"k") is None
    assert db.exists(b"k") is False


def test_delete_missing_key():
    db, _ = make_db()
    assert db.delete(b"k") == 0


def test_delete_no_keys():
    db, _ = make_db()
    assert db.delete() == 0


def test_delete_several_keys_counts_only_existing():
    db, _ = make_db()
    db.set(b"a", b"1", ValueType.STRING)
    db.set(b"b", b"2", ValueType.STRING)
    assert db.delete(b"a", b"missing", b"b") == 2
    assert db.exists(b"a") is False
    assert db.exists(b"b") is False


def test_delete_duplicate_keys_counts_once():
    db, _ = make_db()
    db.set(b"k", b"v", ValueType.STRING)
    assert db.delete(b"k", b"k") == 1


def test_delete_expired_key_is_not_counted():
    db, _clock = make_db(now=100.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.delete(b"k") == 0
    assert b"k" not in db._entries


def test_delete_works_for_any_type():
    db, _ = make_db()
    db.set(b"l", [b"a"], ValueType.LIST)
    db.set(b"s", {b"a"}, ValueType.SET)
    db.set(b"h", {b"f": b"v"}, ValueType.HASH)
    assert db.delete(b"l", b"s", b"h") == 3


def test_delete_leaves_other_keys_untouched():
    db, _ = make_db()
    db.set(b"a", b"1", ValueType.STRING)
    db.set(b"b", b"2", ValueType.STRING)
    db.delete(b"a")
    assert db.get(b"b") == b"2"


def test_keys_empty_database():
    db, _ = make_db()
    assert db.keys() == []


def test_keys_returns_all_live_keys_of_any_type():
    db, _ = make_db()
    db.set(b"a", b"1", ValueType.STRING)
    db.set(b"b", [b"x"], ValueType.LIST)
    db.set(b"c", {b"x"}, ValueType.SET)
    assert sorted(db.keys()) == [b"a", b"b", b"c"]


def test_keys_skips_and_removes_expired():
    db, _clock = make_db(now=100.0)
    db.set(b"live", b"1", ValueType.STRING)
    db.set(b"dead", b"2", ValueType.STRING)
    db._entries[b"dead"].expiry = 100.0
    assert db.keys() == [b"live"]
    assert b"dead" not in db._entries


def test_keys_keeps_not_yet_expired():
    db, _clock = make_db(now=99.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.keys() == [b"k"]


def test_type_of_each_type():
    db, _ = make_db()
    db.set(b"s", b"v", ValueType.STRING)
    db.set(b"l", [b"a"], ValueType.LIST)
    db.set(b"st", {b"a"}, ValueType.SET)
    db.set(b"h", {b"f": b"v"}, ValueType.HASH)
    db.set(b"z", {b"m": 1.0}, ValueType.ZSET)
    assert db.type_of(b"s") == "string"
    assert db.type_of(b"l") == "list"
    assert db.type_of(b"st") == "set"
    assert db.type_of(b"h") == "hash"
    assert db.type_of(b"z") == "zset"


def test_type_of_missing_key():
    db, _ = make_db()
    assert db.type_of(b"k") == "none"


def test_type_of_expired_key():
    db, _clock = make_db(now=100.0)
    db.set(b"k", b"v", ValueType.STRING)
    db._entries[b"k"].expiry = 100.0
    assert db.type_of(b"k") == "none"
    assert b"k" not in db._entries


def test_get_or_create_creates_missing_key():
    db, _ = make_db()
    value = db.get_or_create(b"k", ValueType.LIST, list)
    assert value == []
    assert db.get(b"k") is value
    assert db.type_of(b"k") == "list"


def test_get_or_create_returns_existing_object():
    db, _ = make_db()
    first = db.get_or_create(b"k", ValueType.LIST, list)
    first.append(b"a")
    second = db.get_or_create(b"k", ValueType.LIST, list)
    assert second is first
    assert second == [b"a"]


def test_get_or_create_does_not_call_factory_for_existing_key():
    db, _ = make_db()
    db.set(b"k", [b"a"], ValueType.LIST)

    def boom():
        raise AssertionError("factory must not be called")

    assert db.get_or_create(b"k", ValueType.LIST, boom) == [b"a"]


def test_get_or_create_wrong_type_raises_and_keeps_value():
    db, _ = make_db()
    db.set(b"k", b"v", ValueType.STRING)
    with pytest.raises(WrongTypeError):
        db.get_or_create(b"k", ValueType.LIST, list)
    assert db.get(b"k") == b"v"


def test_get_or_create_keeps_empty_existing_collection():
    db, _ = make_db()
    empty = []
    db.set(b"k", empty, ValueType.LIST)
    assert db.get_or_create(b"k", ValueType.LIST, list) is empty


def test_get_or_create_expired_key_creates_fresh_value():
    db, clock = make_db(now=0.0)
    db.set(b"k", [b"old"], ValueType.LIST)
    db.set_expiry(b"k", 100.0)
    clock.now = 100.0
    value = db.get_or_create(b"k", ValueType.LIST, list)
    assert value == []
    assert db._entries[b"k"].expiry is None


def test_get_or_create_existing_key_keeps_expiry():
    db, _ = make_db()
    db.set(b"k", [b"a"], ValueType.LIST)
    db.set_expiry(b"k", 100.0)
    db.get_or_create(b"k", ValueType.LIST, list)
    assert db._entries[b"k"].expiry == 100.0
