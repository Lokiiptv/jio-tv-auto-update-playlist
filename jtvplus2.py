import requests
import json
import os
import sys

# Configuration
REMOTE_JSON_URL = "https://upaidworker.streamxlive.workers.dev/"
LOCAL_JSON_FILE = "jtv.json"          # local file to use first
USER_AGENT = "Sayan10"
OUTPUT_FILE = "jtvplus2.m3u"

def load_channels_from_json(data):
    """Extract channel list from JSON (list or dict with 'channels' key)."""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "channels" in data:
        return data["channels"]
    else:
        raise ValueError("JSON is not a list nor an object with 'channels' key.")

def fetch_json_source():
    """Try local file first, then remote URL."""
    # 1. Try local file
    if os.path.exists(LOCAL_JSON_FILE):
        try:
            with open(LOCAL_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Loaded local file: {LOCAL_JSON_FILE}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Local file error: {e}. Falling back to remote.")
    # 2. Fallback to remote
    print(f"Fetching from {REMOTE_JSON_URL} ...")
    resp = requests.get(REMOTE_JSON_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()

def generate_m3u():
    try:
        json_data = fetch_json_source()
        channels = load_channels_from_json(json_data)
        print(f"Found {len(channels)} channels. Building M3U...")

        m3u_lines = ["#EXTM3U"]
        processed = 0

        for ch in channels:
            ch_id = ch.get("id", "")
            name = ch.get("name", "Unknown")
            stream_url = ch.get("url", "")
            cookie = ch.get("cookie", "")
            key_id = ch.get("keyId", "")
            key = ch.get("key", "")

            # Skip incomplete entries
            if not all([stream_url, cookie, key_id, key]):
                print(f"  Skipping '{name}' – missing required data.")
                continue

            license_key = f"{key_id}:{key}"
            group = ch.get("category", "Sports")

            # EXTINF
            m3u_lines.append(
                f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="" group-title="{group}",{name}'
            )
            # KODIPROP for ClearKey
            m3u_lines.append("#KODIPROP:inputstream.adaptive.manifest_type=mpd")
            m3u_lines.append("#KODIPROP:inputstream.adaptive.license_type=clearkey")
            m3u_lines.append(f"#KODIPROP:inputstream.adaptive.license_key={license_key}")
            # VLC user-agent
            m3u_lines.append(f"#EXTVLCOPT:http-user-agent={USER_AGENT}")
            # HTTP headers as JSON
            headers = {
                "cookie": cookie,
                "Origin": "https://www.jiotv.com/",
                "Referer": "https://www.jiotv.com/",
            }
            headers_json = json.dumps(headers, separators=(',', ':'))
            m3u_lines.append(f"#EXTHTTP:{headers_json}")
            # Stream URL
            m3u_lines.append(stream_url)
            m3u_lines.append("")   # blank line
            processed += 1

        # Write file
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))

        print(f"\n✅ Playlist saved as: {OUTPUT_FILE}")
        print(f"   Total channels in source: {len(channels)}")
        print(f"   Processed (with all data): {processed}")
        print(f"   Skipped: {len(channels) - processed}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    generate_m3u()
