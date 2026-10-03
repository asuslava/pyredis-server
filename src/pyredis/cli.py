import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyredis",
        description="A Redis-compatible server written in Python",
    )
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--port", type=int, default=6379, help="port to listen on")
    parser.add_argument("--dir", default=".", help="directory for the AOF file")
    args = parser.parse_args()

    print(f"pyredis would start on {args.host}:{args.port}, data dir: {args.dir}")


if __name__ == "__main__":
    main()