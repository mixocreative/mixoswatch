"""One-time script to build nippon_colors_raw.json from nipponcolors.com.

Fetches the HTML to get kanji+romaji+index list, then queries
/php/io.php?color=ROMAJI for CMYK+RGB per color.
Outputs scripts/source_data/nippon_colors_raw.json as a flat list.
"""
from __future__ import annotations
import json, re, time, urllib.request
from pathlib import Path

HTML_URL = "https://nipponcolors.com/"
API_URL  = "https://nipponcolors.com/php/io.php?color={}"
OUT      = Path("scripts/source_data/nippon_colors_raw.json")

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_cmyk_str(s: str) -> list[int]:
    """Parse 12-char string like '002073024000' -> [2, 73, 24, 0]"""
    return [int(s[i:i+3]) for i in range(0, 12, 3)]

def hex_from_rgb6(rgb6: str) -> str:
    return "#" + rgb6.upper()

def main():
    print("Fetching HTML...")
    html = fetch(HTML_URL)
    matches = re.findall(r'<li id="col(\d+)"><div><a[^>]+>([^<]+)</a>', html)
    print(f"Found {len(matches)} color entries in HTML")

    entries = []
    for idx_str, text in matches:
        parts = text.split(", ", 1)
        kanji  = parts[0].strip()
        romaji = parts[1].strip() if len(parts) > 1 else ""
        idx    = idx_str.zfill(3)

        try:
            api_url = API_URL.format(romaji)
            raw = fetch(api_url)
            data = json.loads(raw)
            cmyk_str = data.get("cmyk", "000000000000")
            rgb6     = data.get("rgb", "000000")
            cmyk_list = parse_cmyk_str(cmyk_str)
            hex_val   = hex_from_rgb6(rgb6)
        except Exception as e:
            print(f"  WARN {idx} {romaji}: {e}")
            # Fall back to computing from hex if available
            cmyk_list = [0, 0, 0, 0]
            hex_val   = "#000000"

        entries.append({
            "index":    idx,
            "name":     kanji,
            "pronounce": romaji,
            "hex":      hex_val,
            "cmyk":     cmyk_list,
        })
        print(f"  {idx} ({romaji}) -> {hex_val} CMYK={cmyk_list}")
        time.sleep(0.05)  # polite throttle

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} with {len(entries)} entries")

if __name__ == "__main__":
    main()
