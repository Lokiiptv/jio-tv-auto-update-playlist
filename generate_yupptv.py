#!/usr/bin/env python3
"""
Generate YuppTV M3U playlist with timestamp to force updates.
"""

import requests
import json
import time
import sys
from datetime import datetime
from urllib.parse import quote_plus

# ---------- Configuration ----------
API_BASE = "https://yuppfast-api.revlet.net/service/api/v1"
TOKEN_URL = f"{API_BASE}/get/token"
CHANNELS_URL = f"{API_BASE}/tvguide/channels"
STREAM_URL = f"{API_BASE}/page/stream"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Tenant-Code": "yuppfast",
    "Origin": "https://www.yupptv.com",
    "Referer": "https://www.yupptv.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}

BOX_ID = "3b6f5839-0b53-aa06-7a80-023047a6357c"
OUTPUT_FILE = "./yupptvfast.m3u"
SLEEP_BETWEEN = 0.3  # seconds

# ---------- Logging ----------
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ---------- Main ----------
def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # 1. Get token
        log("Requesting token...")
        resp = session.get(TOKEN_URL, params={
            "tenant_code": "yuppfast",
            "box_id": BOX_ID,
            "product": "yuppfast",
            "device_id": "5",
            "display_lang_code": "ENG",
            "device_sub_type": "Chrome,145.0.0.0,Windows",
            "client_app_version": "1",
            "timezone": "Asia/Calcutta"
        })
        resp.raise_for_status()
        data = resp.json()
        session_id = data["response"]["sessionId"]
        log(f"Session ID: {session_id}")

        # Add session header for subsequent requests
        session.headers["Session-Id"] = session_id
        session.headers["Box-Id"] = BOX_ID

        # 2. Get channel list
        log("Fetching channel list...")
        resp = session.get(CHANNELS_URL, params={
            "filter": "genreCode:all;langCode:ENG,HIN,TAM,MAR,BEN,TEL,KAN,BHO,GUA,PUN,ASS,URD"
        })
        resp.raise_for_status()
        channels = resp.json()["response"]["data"]
        total = len(channels)
        log(f"Found {total} channels")

        # 3. Build playlist
        playlist = [
            "#EXTM3U",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Source: YuppTV API",
            ""  # blank line
        ]

        success = 0
        failed = 0

        for idx, ch in enumerate(channels, 1):
            try:
                path = ch["target"]["path"]
                epg = ch["id"]
                name = ch["display"]["title"]
                logo = ch["display"]["imageUrl"].replace(
                    "common,",
                    "https://d229kpbsb5jevy.cloudfront.net/yuppfast/content/common/"
                )

                # EXTINF line
                playlist.append(
                    f'#EXTINF:-1 tvg-id="{epg}" tvg-chno="{epg}" tvg-name="{name}" tvg-logo="{logo}",{epg} {name}'
                )

                # Get stream URL
                encoded = quote_plus(path)
                resp = session.get(STREAM_URL, params={"path": encoded})
                if resp.status_code == 200:
                    stream_data = resp.json()
                    if stream_data.get("status") and stream_data["response"]["streams"]:
                        url = stream_data["response"]["streams"][0]["url"]
                        playlist.append(url)
                        success += 1
                        log(f"[{idx}/{total}] {name} → OK")
                    else:
                        playlist.append("")
                        failed += 1
                        log(f"[{idx}/{total}] {name} → No stream")
                else:
                    playlist.append("")
                    failed += 1
                    log(f"[{idx}/{total}] {name} → HTTP {resp.status_code}")

                time.sleep(SLEEP_BETWEEN)

            except Exception as e:
                playlist.append("")
                failed += 1
                log(f"[{idx}/{total}] Error for {name}: {str(e)}")

        # 4. Write file
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(playlist))

        log(f"\n{'='*50}")
        log(f"Playlist written to {OUTPUT_FILE}")
        log(f"Total: {total}, Success: {success}, Failed: {failed}")
        log(f"{'='*50}")

        # Exit with failure if too many failures (e.g., >50%)
        if failed > total * 0.5:
            log("Too many failures – exiting with error.")
            sys.exit(1)

    except Exception as e:
        log(f"FATAL: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
