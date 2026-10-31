"""Tests for active key expiration."""

import asyncio

import pytest

from pyredis.expiration import active_expiration_loop
from pyredis.storage import Database, ValueType


def test_active_expire_cycle_basic():
    current_time = 1000.0
    db = Database(clock=lambda: current_time)

    # Set 5 permanent keys (no expiry)
    for i in range(5):
        db.set(f"perm:{i}".encode(), b"val", ValueType.STRING)

    # Set 10 expiring keys: 6 expire at 1050, 4 expire at 1200
    for i in range(6):
        db.set(f"exp_soon:{i}".encode(), b"val", ValueType.STRING, expiry=1050.0)
    for i in range(4):
        db.set(f"exp_later:{i}".encode(), b"val", ValueType.STRING, expiry=1200.0)

    # At time 1000: nothing is expired
    sampled, expired = db.active_expire_cycle(sample_size=20)
    assert sampled == 10  # Only sampled keys with expiry set
    assert expired == 0
    assert len(db.keys()) == 15

    # Advance time to 1060: the 6 keys have expired
    current_time = 1060.0
    sampled, expired = db.active_expire_cycle(sample_size=20)
    assert expired == 6
    assert len(db.keys()) == 9  # 15 - 6 = 9


@pytest.mark.asyncio
async def test_active_expiration_loop():
    current_time = 1000.0
    db = Database(clock=lambda: current_time)

    # Set 3 expiring keys
    db.set(b"k1", b"v", ValueType.STRING, expiry=1050.0)
    db.set(b"k2", b"v", ValueType.STRING, expiry=1050.0)
    db.set(b"k3", b"v", ValueType.STRING, expiry=1200.0)

    # Start loop with very fast tick (0.01s)
    task = asyncio.create_task(active_expiration_loop(db, interval=0.01))

    # Advance time past k1 and k2 expiry
    current_time = 1060.0

    # Let the loop run 1 tick
    await asyncio.sleep(0.03)

    # k1 and k2 should be actively removed without ever reading them!
    assert db.exists(b"k1") is False
    assert db.exists(b"k2") is False
    assert db.exists(b"k3") is True

    # Cancel background task cleanly
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
