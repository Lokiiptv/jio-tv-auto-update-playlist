import requests

# JSON source
JSON_URL = "https://m3u-86e.pages.dev/jtv-mb.json"

# Output playlist
OUTPUT_FILE = "jtv2.m3u"

# Download JSON
response = requests.get(JSON_URL)
response.raise_for_status()
channels = response.json()

with open(OUTPUT_FILE, "w", encoding="utf-8") as m3u:
    m3u.write("#EXTM3U\n")

    for ch in channels:
        name = ch.get("name", "")
        tvg_id = ch.get("id", "")
        logo = ch.get("logo", "")
        group = ch.get("group", "Other")

        mpd_url = ch.get("mpd_url", "")
        license_url = ch.get("license_url", "")
        stream_type = ch.get("type", "").lower()

        # Get cookie (__hdnea__)
        cookie = ch.get("headers", {}).get("cookie", "")

        # Append cookie as query string
        stream_url = mpd_url
        if cookie:
            if "?" in mpd_url:
                stream_url += "&" + cookie
            else:
                stream_url += "?" + cookie

        # Write channel info
        m3u.write(
            f'#EXTINF:-1 tvg-id="{tvg_id}" '
            f'tvg-name="{name}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}",{name}\n'
        )

        # DASH stream
        if stream_type == "dash":
            m3u.write("#KODIPROP:inputstream.adaptive.manifest_type=mpd\n")

        # ClearKey license URL
        if license_url:
            m3u.write("#KODIPROP:inputstream.adaptive.license_type=clearkey\n")
            m3u.write(
                f"#KODIPROP:inputstream.adaptive.license_key={license_url}\n"
            )

        # Stream URL
        m3u.write(stream_url + "\n\n")

print(f"Successfully created '{OUTPUT_FILE}' with {len(channels)} channels.")
