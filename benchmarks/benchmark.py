import argparse
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from pyredis.protocol import serialize


def worker_task(host: str, port: int, commands: list[bytes]) -> list[float]:
    latencies = []
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        for cmd_bytes in commands:
            t0 = time.perf_counter()
            s.sendall(cmd_bytes)

            data = bytearray()
            while b"\r\n" not in data:
                chunk = s.recv(4096)
                if not chunk:
                    return latencies
                data.extend(chunk)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
    finally:
        s.close()
    return latencies


def benchmark_command(
    name: str,
    raw_commands: list[list[bytes]],
    host: str = "127.0.0.1",
    port: int = 6379,
    concurrency: int = 20,
) -> None:
    serialized = [serialize(cmd) for cmd in raw_commands]
    total_requests = len(serialized)

    batch_size = (total_requests + concurrency - 1) // concurrency
    batches = [
        serialized[i : i + batch_size] for i in range(0, total_requests, batch_size)
    ]

    print(
        f"\nRunning benchmark: {name} ({total_requests:,} requests, {concurrency} clients)..."
    )

    start_time = time.perf_counter()

    latencies = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_task, host, port, batch) for batch in batches]
        for f in futures:
            latencies.extend(f.result())

    total_time = time.perf_counter() - start_time
    if not latencies:
        print("No successful requests recorded")
        return

    rps = len(latencies) / total_time
    latencies.sort()
    avg_lat = statistics.mean(latencies)
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print("=" * 55)
    print(f" Benchmark: {name}")
    print("=" * 55)
    print(f" Requests:     {len(latencies):,}")
    print(f" Concurrency:  {concurrency}")
    print(f" Time taken:   {total_time:.3f} seconds")
    print(f" Throughput:   {rps:,.1f} requests/sec")
    print(f" Avg Latency:  {avg_lat:.2f} ms")
    print(f" P50 (Median): {p50:.2f} ms")
    print(f" P95 Latency:  {p95:.2f} ms")
    print(f" P99 Latency:  {p99:.2f} ms")
    print("=" * 55)


def main() -> None:
    parser = argparse.ArgumentParser(description="PyRedis Benchmark Tool")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=6379, help="Server port")
    parser.add_argument(
        "-n", "--requests", type=int, default=5000, help="Total requests per test"
    )
    parser.add_argument(
        "-c", "--concurrency", type=int, default=20, help="Parallel client connections"
    )
    args = parser.parse_args()

    n = args.requests

    ping_cmds = [[b"PING"] for _ in range(n)]
    benchmark_command("PING", ping_cmds, args.host, args.port, args.concurrency)

    set_cmds = [[b"SET", f"key:{i}".encode(), f"val:{i}".encode()] for i in range(n)]
    benchmark_command("SET", set_cmds, args.host, args.port, args.concurrency)

    get_cmds = [[b"GET", f"key:{i}".encode()] for i in range(n)]
    benchmark_command("GET", get_cmds, args.host, args.port, args.concurrency)

    lpush_cmds = [[b"LPUSH", b"bench_list", f"elem:{i}".encode()] for i in range(n)]
    benchmark_command("LPUSH", lpush_cmds, args.host, args.port, args.concurrency)


if __name__ == "__main__":
    main()
