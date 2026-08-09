#!/usr/bin/env python3


import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # pip install requests

# -------------------- Configuration --------------------
DEFAULT_JSON_URL = "https://m3u-86e.pages.dev/jtv-mb.json"
DEFAULT_OUTPUT = "jtv2.m3u"
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 30
USER_AGENT = "Virat Kohli"

# -------------------- Logging Setup --------------------
def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Configure logging to console and optionally a file."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

# -------------------- Fetch with Retries --------------------
def fetch_json(url: str, retries: int = DEFAULT_RETRIES, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:
    """
    Fetch JSON from URL with retry logic and cache-busting.
    Returns list of channel dicts.
    """
    headers = {"User-Agent": USER_AGENT}
    # Add timestamp to avoid caching
    cache_buster = f"?t={int(time.time())}"
    full_url = url + cache_buster

    for attempt in range(1, retries + 1):
        try:
            logging.info(f"Fetching JSON (attempt {attempt}/{retries}) from {url}")
            resp = requests.get(full_url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise ValueError(f"Expected list, got {type(data).__name__}")
            logging.info(f"Successfully fetched {len(data)} channels")
            return data
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
    # Should never get here
    return []

# -------------------- Generate M3U Content --------------------
def generate_m3u(channels: List[Dict[str, Any]], source_url: str) -> str:
    """
    Convert channel list to M3U8 playlist content.
    Returns the complete text.
    """
    lines = []
    lines.append("#EXTM3U")
    # Include generation metadata
    lines.append(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"# Source: {source_url}")
    # Optionally add a hash of the source data to detect changes
    source_hash = hashlib.md5(json.dumps(channels, sort_keys=True).encode()).hexdigest()
    lines.append(f"# Source-Hash: {source_hash}")
    lines.append("")  # blank line for readability

    for ch in channels:
        name = ch.get("name", "Unknown")
        tvg_id = ch.get("id", "")
        logo = ch.get("logo", "")
        group = ch.get("group", "Other")
        mpd_url = ch.get("mpd_url", "")
        license_url = ch.get("license_url", "")
        stream_type = ch.get("type", "").lower()
        # Cookie handling
        cookie = ch.get("headers", {}).get("cookie", "")

        # Build stream URL with cookie as query string
        stream_url = mpd_url
        if cookie:
            separator = "&" if "?" in stream_url else "?"
            stream_url += separator + cookie

        # Write EXTINF line
        extinf = (
            f'#EXTINF:-1 tvg-id="{tvg_id}" '
            f'tvg-name="{name}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}",{name}'
        )
        lines.append(extinf)

        # KODI/DASH properties
        if stream_type == "dash":
            lines.append("#KODIPROP:inputstream.adaptive.manifest_type=mpd")
        if license_url:
            lines.append("#KODIPROP:inputstream.adaptive.license_type=clearkey")
            lines.append(f"#KODIPROP:inputstream.adaptive.license_key={license_url}")

        # Stream URL
        lines.append(stream_url)
        lines.append("")  # blank line between entries

    return "\n".join(lines)

# -------------------- Safe Write with Change Detection --------------------
def write_if_changed(content: str, output_path: Path) -> bool:
    """
    Write content to a temporary file and rename atomically.
    If the existing file has the same content, do nothing.
    Returns True if file was written/updated, False if unchanged.
    """
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content if file exists
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                old_content = f.read()
            if old_content == content:
                logging.info(f"Content unchanged; skipping write to {output_path}")
                return False
        except Exception as e:
            logging.warning(f"Could not read existing file: {e}")

    # Write to temporary file
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        # Rename atomically (works on Unix, on Windows may need extra care)
        tmp_path.replace(output_path)
        logging.info(f"Successfully written {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to write file: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise

# -------------------- Main --------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate M3U playlist from JSON source"
    )
    parser.add_argument(
        "-u", "--url",
        default=os.getenv("JSON_URL", DEFAULT_JSON_URL),
        help=f"JSON source URL (default: {DEFAULT_JSON_URL})"
    )
    parser.add_argument(
        "-o", "--output",
        default=os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT),
        help=f"Output M3U file (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=int(os.getenv("RETRIES", DEFAULT_RETRIES)),
        help=f"Number of retries (default: {DEFAULT_RETRIES})"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--log-file",
        help="Write logs to this file as well"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite even if content unchanged"
    )
    args = parser.parse_args()

    setup_logging(args.verbose, args.log_file)
    logging.info("Starting M3U generator")

    try:
        # Fetch data
        channels = fetch_json(args.url, retries=args.retries)
        if not channels:
            logging.error("No channels received; aborting.")
            return 1

        # Generate content
        content = generate_m3u(channels, args.url)

        # Write output
        output_path = Path(args.output)
        if args.force:
            # Write directly without change detection
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            logging.info(f"Forced write to {output_path}")
        else:
            written = write_if_changed(content, output_path)
            if not written:
                logging.info("No changes detected; file remains untouched.")

        logging.info("Done.")
        return 0

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=args.verbose)
        return 1

if __name__ == "__main__":
    sys.exit(main())
