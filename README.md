# PyRedis

A lightweight Redis-compatible in-memory server written in Python using `asyncio`. It is wire-compatible with `redis-cli` and supports the RESP2 protocol.

## Features

- **RESP2 Protocol**: Custom streaming parser and serializer.
- **Data Structures**: Strings, Lists, Hashes, Sets, and Sorted Sets (ZSets).
- **Key Expiry**: Passive expiration on access and active background sampling every 100ms.
- **Persistence**: Append-Only File (AOF) logging and automatic replay on startup.
- **Transactions**: `MULTI`, `EXEC`, and `DISCARD` with per-client command queuing.
- **Pub/Sub**: `SUBSCRIBE`, `UNSUBSCRIBE`, and `PUBLISH` for real-time messaging.
- **Standard Library Only**: Core server uses zero third-party runtime dependencies.

## Supported Commands

- **Connection**: `PING`, `QUIT`
- **Keys**: `DEL`, `EXISTS`, `EXPIRE`, `TTL`, `PERSIST`
- **Strings**: `SET`, `GET`
- **Lists**: `LPUSH`, `RPUSH`, `LPOP`, `RPOP`, `LLEN`, `LRANGE`
- **Hashes**: `HSET`, `HGET`, `HDEL`, `HEXISTS`, `HLEN`, `HGETALL`
- **Sets**: `SADD`, `SMEMBERS`, `SREM`, `SISMEMBER`, `SCARD`
- **Sorted Sets**: `ZADD`, `ZSCORE`, `ZCARD`, `ZREM`, `ZRANGE`
- **Transactions**: `MULTI`, `EXEC`, `DISCARD`
- **Pub/Sub**: `SUBSCRIBE`, `UNSUBSCRIBE`, `PUBLISH`

## Quickstart

### Run with Docker Compose

```bash
docker compose up --build
```

### Run Locally

Requires Python 3.11+:

```bash
python3 src/pyredis/cli.py --host 127.0.0.1 --port 6379
```

### Connect with `redis-cli`

```bash
redis-cli -h 127.0.0.1 -p 6379
```

## Testing & Benchmarks

Run the test suite:
```bash
pytest -v
```

Run benchmarks:
```bash
python3 benchmarks/benchmark.py -n 5000 -c 20
```
