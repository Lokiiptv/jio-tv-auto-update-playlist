import re
import json
import requests

def fetch_and_filter_sports_m3u(playlist_url, output_file):
    """
    Download an M3U playlist, extract only Sports channels,
    and write them in the desired format to a new file.
    """
    # Download the playlist
    try:
        response = requests.get(playlist_url)
        response.raise_for_status()
        lines = response.text.splitlines()
    except requests.exceptions.RequestException as e:
        print(f"Failed to download playlist: {e}")
        return

    sports_entries = []
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i].strip()
        # Look for the start of a channel entry
        if line.startswith('#EXTINF:'):
            # Store the EXTINF line
            extinf_line = line

            # Advance to read subsequent metadata lines
            i += 1
            url = None
            license_key = None
            cookie = None

            # Keep reading until we hit a URL (http or https)
            while i < total_lines:
                current = lines[i].strip()
                if current.startswith('http://') or current.startswith('https://'):
                    url = current
                    i += 1
                    break
                elif current.startswith('#KODIPROP:inputstream.adaptive.license_key='):
                    # Extract the full key (e.g., "e6bd...:962e...")
                    license_key = current.replace('#KODIPROP:inputstream.adaptive.license_key=', '').strip()
                elif current.startswith('#EXTHTTP:'):
                    try:
                        # Extract the JSON part
                        json_str = current.replace('#EXTHTTP:', '').strip()
                        data = json.loads(json_str)
                        cookie = data.get('cookie')
                    except:
                        pass
                # Ignore other lines like #KODIPROP:manifest_type, #EXTVLCOPT, etc.
                i += 1

            # If we got a URL, create an entry
            if url:
                # Parse the EXTINF line to get tvg-id, tvg-logo, and channel name
                # Example: #EXTINF:-1 tvg-id="143" group-title="English" tvg-logo="...",CNBC TV18 Prime
                # We'll extract using regex
                tvg_id_match = re.search(r'tvg-id="([^"]+)"', extinf_line)
                tvg_logo_match = re.search(r'tvg-logo="([^"]+)"', extinf_line)
                # Channel name is after the last comma
                name_match = re.search(r',([^,]+)$', extinf_line)
                channel_name = name_match.group(1).strip() if name_match else ""

                # Ensure the group-title is "Sports" (we already filtered, but double-check)
                if 'group-title="Sports"' in extinf_line:
                    entry = {
                        'tvg_id': tvg_id_match.group(1) if tvg_id_match else '',
                        'tvg_logo': tvg_logo_match.group(1) if tvg_logo_match else '',
                        'channel_name': channel_name,
                        'license_key': license_key or '',
                        'cookie': cookie or '',
                        'url': url
                    }
                    sports_entries.append(entry)
        else:
            i += 1

    # Build the new M3U content
    output_lines = ['#EXTM3U']
    for entry in sports_entries:
        # EXTINF line
        extinf = (f'#EXTINF:-1 tvg-id="{entry["tvg_id"]}" '
                  f'tvg-name="{entry["channel_name"]}" '
                  f'tvg-logo="{entry["tvg_logo"]}" '
                  f'group-title="Sports",{entry["channel_name"]}')
        output_lines.append(extinf)

        # KODIPROP lines
        output_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=mpd')
        output_lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
        if entry['license_key']:
            output_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={entry["license_key"]}')

        # EXTVLCOPT (fixed as per your example)
        output_lines.append('#EXTVLCOPT:http-user-agent=Sayan10')

        # EXTHTTP with cookie, Origin, Referer
        if entry['cookie']:
            exthttp = (f'#EXTHTTP:{{"cookie":"{entry["cookie"]}",'
                       f'"Origin":"https://www.jiotv.com/",'
                       f'"Referer":"https://www.jiotv.com/"}}')
            output_lines.append(exthttp)

        # Stream URL
        output_lines.append(entry['url'])
        output_lines.append('')  # blank line between entries

    # Write the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"✅ Extracted {len(sports_entries)} sports channel(s) to '{output_file}'")

if __name__ == "__main__":
    playlist_url = "https://raw.githubusercontent.com/SSK4570live/TV-/refs/heads/main/jtv.m3u"
    output_file = "star3.m3u"
    fetch_and_filter_sports_m3u(playlist_url, output_file)
