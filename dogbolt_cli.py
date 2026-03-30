#!/usr/bin/env python3
"""
dogbolt-cli — upload a binary to dogbolt.org and download decompiled sources.

Usage:
    db -f <binary> [-o <output-dir>] [-d <decompilers>] [-v]

See db --help for full options.
"""

import os
import sys
import time
import json
import argparse

import requests

PROG = os.path.basename(sys.argv[0])

RETRY_SLEEP = 30
RETRY_COUNT = 10
REQUESTS_PER_DECOMPILER = 3

DECOMPILER_NAMES = {
    "BinaryNinja": "binary-ninja",
    "Ghidra": "ghidra",
    "Hex-Rays": "hex-rays",
}

DEFAULT_DECOMPILERS = set(DECOMPILER_NAMES.keys())


def log(msg, verbose):
    if verbose:
        print(f"{PROG}: {msg}", file=sys.stderr)


def err(msg):
    print(f"{PROG}: {msg}", file=sys.stderr)


def upload_binary(file_path, verbose):
    file_size = os.path.getsize(file_path)
    log(f"uploading {file_path} ({file_size} bytes)", verbose)
    if file_size > 2 * 1024 * 1024:
        err("binary is too large (must be smaller than 2 MB)")
        sys.exit(1)

    response = requests.post(
        "https://dogbolt.org/api/binaries/",
        files={"file": open(file_path, "rb")},
    )
    binary_id = response.json().get("id")
    log(f"binary id: {binary_id}", verbose)
    return binary_id


def download_result(
    result,
    done_decompiler_keys,
    request_count_by_decompiler_key,
    binary_id,
    output_dir,
    decompilers,
    verbose,
):
    decompiler_name = result["decompiler"]["name"]
    decompiler_version = result["decompiler"]["version"]
    decompiler_key = f"{decompiler_name}-{decompiler_version}"

    if decompiler_name not in decompilers:
        return

    if decompiler_key in done_decompiler_keys:
        return

    if decompiler_name in DECOMPILER_NAMES:
        decompiler_name = DECOMPILER_NAMES[decompiler_name]

    output_extension = "cpp" if decompiler_name == "snowman" else "c"
    output_path = os.path.join(output_dir, f"{decompiler_name}.{output_extension}")
    os.makedirs(output_dir, exist_ok=True)

    error = result.get("error")
    if error == "Exceeded time limit":
        if (
            request_count_by_decompiler_key.get(decompiler_key, 0)
            >= REQUESTS_PER_DECOMPILER
        ):
            err(f"{decompiler_key}: timeout, giving up")
            done_decompiler_keys.add(decompiler_key)
            return
        request_count_by_decompiler_key[decompiler_key] = (
            request_count_by_decompiler_key.get(decompiler_key, 0) + 1
        )
        err(
            f"{decompiler_key}: timeout, retrying "
            f"({request_count_by_decompiler_key[decompiler_key]}/{REQUESTS_PER_DECOMPILER})"
        )
        requests.post(
            f"https://dogbolt.org/api/binaries/{binary_id}/"
            f"decompilations/{result['id']}/rerun/"
        )
        return
    elif error:
        err(f"{decompiler_key}: {error}")
        with open(os.path.join(output_dir, f"{decompiler_key}-error.txt"), "w") as f:
            f.write(error)
        done_decompiler_keys.add(decompiler_key)
        return

    with open(output_path, "wb") as f:
        f.write(requests.get(result["download_url"]).content)
    print(output_path)

    done_decompiler_keys.add(decompiler_key)


def dogbolt_decompile(file_path, output_dir=None, decompilers=None, verbose=False):
    if not file_path or not os.path.isfile(file_path):
        err("invalid file path")
        sys.exit(1)

    binary_id = upload_binary(file_path, verbose)

    response = requests.get("https://dogbolt.org/")
    decompilers_json = json.loads(
        response.text.split(
            '<script id="decompilers_json" type="application/json">'
        )[1].split("</script>")[0]
    )
    api_decompilers = set(decompilers_json.keys())

    if verbose:
        log(f"available decompilers: {', '.join(sorted(api_decompilers))}", verbose)

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(file_path), "src")

    if decompilers is None:
        decompilers = DEFAULT_DECOMPILERS & api_decompilers
        unavailable = DEFAULT_DECOMPILERS - api_decompilers
        if unavailable:
            err(f"not available on API: {', '.join(sorted(unavailable))}")
    else:
        unknown = decompilers - api_decompilers
        if unknown:
            err(f"unknown decompilers: {', '.join(sorted(unknown))}")
        decompilers &= api_decompilers

    log(f"using decompilers: {', '.join(sorted(decompilers))}", verbose)

    done_decompiler_keys = set()
    request_count_by_decompiler_key = {}

    for _retry_step in range(RETRY_COUNT):
        log("fetching results...", verbose)
        response = requests.get(
            f"https://dogbolt.org/api/binaries/{binary_id}/"
            "decompilations/?completed=true"
        )
        for result in response.json()["results"]:
            download_result(
                result,
                done_decompiler_keys,
                request_count_by_decompiler_key,
                binary_id,
                output_dir,
                decompilers,
                verbose,
            )

        if len(done_decompiler_keys) == len(decompilers):
            break

        log(
            f"fetched {len(done_decompiler_keys)}/{len(decompilers)},"
            f" retrying in {RETRY_SLEEP}s",
            verbose,
        )
        time.sleep(RETRY_SLEEP)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--file-path", type=str, help="Path to the file", required=True
    )
    parser.add_argument(
        "-o", "--output-dir", type=str, help="Directory to save the results",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print additional information, including available decompilers from the API",
    )
    parser.add_argument(
        "-d", "--decompilers",
        type=lambda s: set(s.split(",")),
        help=(
            "Comma-separated list of decompilers to use "
            f"(default: all supported: {', '.join(sorted(DEFAULT_DECOMPILERS))})"
        ),
    )
    return parser.parse_args().__dict__


def main():
    dogbolt_decompile(**parse_args())

if __name__ == "__main__":
    main()
