import time
import pytest
from pyredis.storage import Database


@pytest.fixture
def db():
    """Provides a fresh Database instance for each test."""
    return Database()


# --- set_string & get_string Tests ---

def test_set_and_get_string(db):
    db.set_string(b"key1", b"value1")
    assert db.get_string(b"key1") == b"value1"


def test_get_nonexistent_key(db):
    assert db.get_string(b"nonexistent") is None


def test_overwrite_string_updates_value(db):
    db.set_string(b"key1", b"value1")
    db.set_string(b"key1", b"value2")
    assert db.get_string(b"key1") == b"value2"


# --- Expiry & Lazy Deletion Tests ---

def test_key_expires_after_ttl(db):
    db.set_string(b"temp_key", b"temp_val")
    # Manually set expiration to 0.1 seconds in the future
    db._expiry[b"temp_key"] = time.time() + 0.1

    # Key exists initially
    assert db.get_string(b"temp_key") == b"temp_val"

    # Wait for key to expire
    time.sleep(0.15)

    # Lazy deletion should trigger and return None
    assert db.get_string(b"temp_key") is None
    assert b"temp_key" not in db._data
    assert b"temp_key" not in db._types
    assert b"temp_key" not in db._expiry


def test_overwriting_key_clears_expiry(db):
    db.set_string(b"key1", b"val1")
    db._expiry[b"key1"] = time.time() + 0.1  # set expiry

    # Overwrite the key without setting an expiry
    db.set_string(b"key1", b"val2")

    # Ensure expiry was popped from internal dict
    assert b"key1" not in db._expiry

    # Wait past the original expiration time
    time.sleep(0.15)

    # Key should still exist because expiry was cleared
    assert db.get_string(b"key1") == b"val2"


# --- exists Tests ---

def test_exists_returns_true_for_valid_key(db):
    db.set_string(b"key1", b"val1")
    assert db.exists(b"key1") is True


def test_exists_returns_false_for_missing_key(db):
    assert db.exists(b"missing") is False


def test_exists_returns_false_and_cleans_up_expired_key(db):
    db.set_string(b"key1", b"val1")
    db._expiry[b"key1"] = time.time() - 1.0  # Already expired

    assert db.exists(b"key1") is False
    assert b"key1" not in db._data


# --- delete Tests ---

def test_delete_single_key(db):
    db.set_string(b"key1", b"val1")
    deleted_count = db.delete(b"key1")

    assert deleted_count == 1
    assert db.get_string(b"key1") is None
    assert db.exists(b"key1") is False


def test_delete_multiple_keys(db):
    db.set_string(b"k1", b"v1")
    db.set_string(b"k2", b"v2")
    db.set_string(b"k3", b"v3")

    # Delete 2 existing keys and 1 non-existent key
    deleted_count = db.delete(b"k1", b"k2", b"nonexistent")

    assert deleted_count == 2
    assert db.exists(b"k1") is False
    assert db.exists(b"k2") is False
    assert db.exists(b"k3") is True


def test_delete_expired_key_returns_zero(db):
    db.set_string(b"expired_key", b"val")
    db._expiry[b"expired_key"] = time.time() - 1.0  # Already expired

    # Should clean up via _is_expired and not increment deleted_count
    deleted_count = db.delete(b"expired_key")
    assert deleted_count == 0