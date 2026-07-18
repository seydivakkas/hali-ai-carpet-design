"""Download a large ModelScope model file with resumable HTTP ranges."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from modelscope.hub.api import HubApi
from modelscope.hub.file_download import get_file_download_url


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_id")
    parser.add_argument("file_path")
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", default="master")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--chunk-mib", type=int, default=64)
    return parser.parse_args()


def _model_file_size(model_id: str, file_path: str) -> int:
    files = HubApi().get_model_files(model_id, recursive=True)
    for item in files:
        if item.get("Path") == file_path:
            return int(item["Size"])
    raise FileNotFoundError(f"ModelScope file is not listed: {model_id}/{file_path}")


def _signed_url(model_id: str, file_path: str, revision: str) -> str:
    api_url = get_file_download_url(model_id, file_path, revision)
    with requests.get(api_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        return response.url


def _write_state(path: Path, payload: dict[str, object]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def main() -> None:
    args = _parse_args()
    if args.workers < 1 or args.chunk_mib < 1:
        raise ValueError("workers and chunk-mib must be positive")

    expected_size = _model_file_size(args.model_id, args.file_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    partial_path = args.output.with_suffix(args.output.suffix + ".multirange")
    state_path = args.output.with_suffix(args.output.suffix + ".ranges.json")
    chunk_size = args.chunk_mib * 1024 * 1024
    ranges = [
        (start, min(start + chunk_size - 1, expected_size - 1))
        for start in range(0, expected_size, chunk_size)
    ]

    state: dict[str, object] = {
        "model_id": args.model_id,
        "file_path": args.file_path,
        "revision": args.revision,
        "expected_size": expected_size,
        "completed": [],
    }
    if state_path.is_file():
        candidate = json.loads(state_path.read_text(encoding="utf-8"))
        identity = (candidate.get("model_id"), candidate.get("file_path"), candidate.get("expected_size"))
        if identity == (args.model_id, args.file_path, expected_size):
            state = candidate

    completed = {tuple(item) for item in state.get("completed", [])}
    pending = [item for item in ranges if item not in completed]
    with partial_path.open("ab") as output_file:
        output_file.truncate(expected_size)

    signed_url = _signed_url(args.model_id, args.file_path, args.revision)
    state_lock = threading.Lock()
    started_at = time.perf_counter()

    def download_range(byte_range: tuple[int, int]) -> tuple[int, int]:
        start, end = byte_range
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                with requests.get(
                    signed_url,
                    headers={"Range": f"bytes={start}-{end}"},
                    stream=True,
                    timeout=(30, 120),
                ) as response:
                    if response.status_code != 206:
                        raise RuntimeError(f"Range request returned HTTP {response.status_code}")
                    expected_range = f"bytes {start}-{end}/{expected_size}"
                    if response.headers.get("Content-Range") != expected_range:
                        raise RuntimeError(
                            f"Unexpected Content-Range: {response.headers.get('Content-Range')}"
                        )
                    written = 0
                    with partial_path.open("r+b", buffering=0) as output_file:
                        output_file.seek(start)
                        for block in response.iter_content(chunk_size=1024 * 1024):
                            if block:
                                output_file.write(block)
                                written += len(block)
                    if written != end - start + 1:
                        raise OSError(f"Range length mismatch: wrote {written} bytes")
                    return byte_range
            except (OSError, requests.RequestException, RuntimeError) as error:
                last_error = error
                time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"Range {start}-{end} failed after retries: {last_error}")

    print(
        f"Downloading {args.file_path}: {expected_size / 1024**3:.2f} GiB, "
        f"{len(pending)}/{len(ranges)} ranges pending, workers={args.workers}",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_range, byte_range): byte_range for byte_range in pending}
        for future in as_completed(futures):
            byte_range = future.result()
            with state_lock:
                completed.add(byte_range)
                state["completed"] = [list(item) for item in sorted(completed)]
                _write_state(state_path, state)
                done_bytes = sum(end - start + 1 for start, end in completed)
                elapsed = max(time.perf_counter() - started_at, 0.001)
                print(
                    f"Progress {done_bytes / expected_size:.1%} "
                    f"({done_bytes / 1024**3:.2f} GiB, {done_bytes / elapsed / 1024**2:.1f} MiB/s)",
                    flush=True,
                )

    if partial_path.stat().st_size != expected_size or len(completed) != len(ranges):
        raise OSError("Download did not complete all expected byte ranges")
    os.replace(partial_path, args.output)
    state_path.unlink(missing_ok=True)
    print(f"Completed: {args.output} ({expected_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
