import asyncio

from pyredis.storage import Database


async def active_expiration_loop(db: Database, interval: float = 0.1) -> None:

    try:
        while True:
            sampled, expired = db.active_expire_cycle()

            if sampled > 0 and (expired / sampled) > 0.25:
                continue

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass