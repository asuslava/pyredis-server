import argparse
import asyncio
from pyredis.server import RedisServer

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyredis",
        description="A Redis-compatible server written in Python",
    )
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--port", type=int, default=6379, help="port to listen on")
    parser.add_argument("--dir", default=".", help="directory for the AOF file")
    args = parser.parse_args()

    server = RedisServer(host=args.host, port=args.port)
    print(f"PyRedis running on {args.host}:{args.port}")

    print(f"pyredis would start on {args.host}:{args.port}, data dir: {args.dir}")

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nPyRedis shutting down...")


if __name__ == "__main__":
    main()
