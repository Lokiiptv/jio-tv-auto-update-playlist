import requests
import re

def extract_star_sports(playlist_url, output_file):
    """
    Download an M3U playlist, filter only Star Sports channels,
    and save them to a new M3U file with all original metadata.
    """
    try:
        response = requests.get(playlist_url)
        response.raise_for_status()
        lines = response.text.splitlines()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download playlist: {e}")
        return

    output_lines = ['#EXTM3U']
    star_sports_count = 0
    i = 0
    total = len(lines)

    while i < total:
        line = lines[i].strip()
        # Start of a channel entry: #EXTINF:
        if line.startswith('#EXTINF:'):
            # Collect all lines of this entry until we hit a URL (http:// or https://)
            entry_lines = [line]
            i += 1
            # Gather subsequent lines until we find the stream URL
            while i < total:
                current = lines[i].strip()
                if current.startswith(('http://', 'https://')):
                    # This is the stream URL, add it and finish this entry
                    entry_lines.append(current)
                    i += 1
                    break
                else:
                    # This is a metadata line (KODIPROP, EXTVLCOPT, EXTHTTP, etc.)
                    entry_lines.append(current)
                    i += 1
            else:
                # If we finish the loop without finding a URL, we may have an incomplete entry; skip.
                continue

            # Now check if this entry is a Star Sports channel
            # The channel name is after the last comma in the #EXTINF line
            extinf = entry_lines[0]  # First line is #EXTINF
            # Find the channel name: everything after the last comma
            if ',' in extinf:
                channel_name = extinf.rsplit(',', 1)[-1].strip()
            else:
                channel_name = ""

            # Check if "Star Sports" appears (case-insensitive)
            if re.search(r'star\s*sports', channel_name, re.IGNORECASE):
                # Add a blank line before each entry (except the first) for readability
                if output_lines != ['#EXTM3U']:
                    output_lines.append('')
                output_lines.extend(entry_lines)
                star_sports_count += 1
        else:
            i += 1

    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"✅ Found {star_sports_count} Star Sports channel(s). Saved to '{output_file}'.")

if __name__ == "__main__":
    playlist_url = "https://raw.githubusercontent.com/SSK4570live/TV-/refs/heads/main/jtv.m3u"
    output_file = "Star3.m3u"
    extract_star_sports(playlist_url, output_file)
