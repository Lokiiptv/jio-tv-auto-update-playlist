#!/usr/bin/env python3
"""
Generator Script - Generate M3U playlist
"""

import json
import requests
import base64
import concurrent.futures

def b64url_to_hex(b64_str):
    """Convert base64url string to hex string for clearkey format"""
    if not b64_str:
        return ""
    padding = '=' * (4 - (len(b64_str) % 4)) if len(b64_str) % 4 != 0 else ''
    try:
        return base64.urlsafe_b64decode(b64_str + padding).hex()
    except Exception:
        return ""

def process_channel(ch):
    """Process a single channel, returning formatted M3U block string or None if invalid"""
    # Actual JSON field names from Geoplus.json
    channel_id = ch.get("id", "")
    name = ch.get("name", "Unknown Channel")
    logo = ch.get("logo", "")
    category = ch.get("group", "")
    mpd = ch.get("mpd_url", "")
    user_agent = ch.get("user_agent", "")
    license_url = ch.get("license_url", "")
    headers_dict = ch.get("headers", {}) or {}
    stream_type = ch.get("type", "dash")
    
    # Skip channels with no stream URL
    if not mpd or mpd.strip() == "":
        return None
    
    lines = []
    # Write EXTINF line
    lines.append(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" group-title="{category}",{name}')
    
    # Write Kodi adaptive stream properties for DASH streams
    if stream_type == "dash":
        lines.append('#KODIPROP:inputstream=inputstream.adaptive')
        lines.append('#KODIPROP:inputstream.adaptive.manifest_type=mpd')
        if license_url:
            # Fetch the actual keys from the license_url
            try:
                # User-Agent is required to bypass the Telegram redirect
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                r = requests.get(license_url, headers=headers, timeout=10)
                if r.status_code == 200 and "keys" in r.text:
                    key_data = r.json()
                    keys = key_data.get("keys", [])
                    if keys:
                        lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
                        for k in keys:
                            kid_hex = b64url_to_hex(k.get("kid", ""))
                            key_hex = b64url_to_hex(k.get("k", ""))
                            if kid_hex and key_hex:
                                lines.append(f'#KODIPROP:inputstream.adaptive.license_key={kid_hex}:{key_hex}')
                                break # Usually one key is enough for Kodi clearkey
                    else:
                        # Fallback if no keys in json
                        lines.append('#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha')
                        lines.append(f'#KODIPROP:inputstream.adaptive.license_key={license_url}')
                else:
                    # Fallback if not returning valid keys JSON
                    lines.append('#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha')
                    lines.append(f'#KODIPROP:inputstream.adaptive.license_key={license_url}')
            except Exception as e:
                # Fallback on network/parsing error
                lines.append('#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha')
                lines.append(f'#KODIPROP:inputstream.adaptive.license_key={license_url}')
    
    # Build stream URL with HTTP headers appended (Kodi style: url|Header=value&Header2=value2)
    url_headers = []
    if user_agent and user_agent not in ("null", ""):
        # User-Agent: encode only spaces (replace with +), keep rest raw
        url_headers.append(f"User-Agent={user_agent.replace(' ', '%20')}")
    
    stream_url = mpd
    query_token = None

    # Append any extra headers from the headers dict (cookie, referer, origin, etc.)
    for hdr_key, hdr_val in headers_dict.items():
        if not hdr_val or hdr_val in ("null", ""):
            continue
        # Jio's __hdnea__ token is validated as a URL query parameter, not
        # as an HTTP Cookie header — a pipe-header Cookie with the same
        # valid, unexpired token still got "access denied", while the same
        # token appended to the URL (?__hdnea__=...) worked. So pull it out
        # of the header list and append it to the URL itself instead.
        if hdr_key.lower() == "cookie" and hdr_val.startswith("__hdnea__="):
            query_token = hdr_val
            continue
        url_headers.append(f"{hdr_key}={hdr_val}")

    if query_token:
        separator = "&" if "?" in stream_url else "?"
        stream_url += f"{separator}{query_token}"

    if url_headers:
        stream_url += "|" + "&".join(url_headers)
    
    lines.append(stream_url)
    return "\n".join(lines) + "\n"

def generate_m3u():
    url = "https://raw.githubusercontent.com/qwerty180506/json/refs/heads/main/Geoplus.json"
    print(f"[*] Fetching channels from API: {url}...")
    
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        channels = response.json()
        print(f"[+] Successfully fetched {len(channels)} channels.")
        print("[*] Fetching clearkeys for channels (this might take a minute)...")
        
        m3u_file = "jtv2.m3u"
        written = 0
        
        # Use ThreadPoolExecutor to fetch license keys concurrently
        with open(m3u_file, "w", encoding="utf-8") as f:
            f.write('#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mitthu786/tvepg/main/tataplay/epg.xml.gz"\n\n')
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                # executor.map preserves input order and runs each channel
                # exactly once (previously channels were submitted twice:
                # once via submit() into an unused dict, and again here via
                # map — doubling every license_url HTTP request for nothing).
                for block in executor.map(process_channel, channels):
                    if block:
                        f.write(block + "\n")
                        written += 1
                        
        print(f"[+] Written {written} channels to {m3u_file}")
        print(f"[*] Playlist generated successfully and saved to {m3u_file}")
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_m3u()
