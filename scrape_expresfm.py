#!/usr/bin/env python3
"""
Scrape played songs from Expres FM radio station.

Fetches the playlist page and extracts artist/title for each song.
Outputs in format compatible with spotify_playlist.py.
"""

import argparse
import re
from playwright.sync_api import sync_playwright

URL = "https://www.expresfm.cz/playlist"


def handle_consent(page):
    """Handle Seznam.cz cookie consent dialog if present."""
    consent_selectors = [
        "button:has-text('Souhlasím')",
        "button:has-text('souhlasím')",
        "button:has-text('Přijmout vše')",
        "button:has-text('Přijmout')",
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        ".scmp_cmpAgreeBtn",
        "[class*='agree']",
        "[class*='consent'] button",
    ]
    for selector in consent_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                print(f"Clicking consent button: {selector}")
                btn.click()
                page.wait_for_timeout(2000)
                return True
        except:
            pass
    return False


def scrape_playlist(headless: bool = True) -> list[tuple[str, str]]:
    """
    Scrape the ExpressFM playlist page.

    Returns list of (artist, title) tuples.
    """
    songs = []

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        page = browser.new_page()

        print(f"Fetching {URL}...")
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Handle consent dialog - try multiple times
        for attempt in range(3):
            if handle_consent(page):
                print("Accepted cookie consent")
                page.wait_for_timeout(3000)
                break
            page.wait_for_timeout(1000)

        # Wait for playlist to load
        try:
            page.wait_for_selector(".playlist__item", timeout=15000)
        except:
            print("Playlist not found, retrying after reload...")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(3000)
            handle_consent(page)
            page.wait_for_timeout(3000)
            page.wait_for_selector(".playlist__item", timeout=15000)

        # Extract all playlist items
        items = page.query_selector_all(".playlist__item")
        print(f"Found {len(items)} playlist items")

        for item in items:
            try:
                # Get artist from <strong> tag
                strong = item.query_selector("strong")
                if not strong:
                    continue

                artist = strong.text_content().strip()

                # Get title - it's the text after </strong> in the paragraph div
                paragraph = item.query_selector(".paragraph")
                if paragraph:
                    full_text = paragraph.text_content().strip()
                    # Remove artist from beginning to get title
                    title = full_text[len(artist):].strip()

                    # Clean up title - remove "(NOVINKA)" suffix if present
                    title = re.sub(r'\s*\(NOVINKA\)\s*$', '', title, flags=re.IGNORECASE)

                    if artist and title:
                        songs.append((artist, title))

            except Exception as e:
                continue

        browser.close()

    return songs


def format_song(artist: str, title: str) -> str:
    """Format artist and title for Spotify search."""
    # Convert to title case for better Spotify matching
    artist = artist.title()
    title = title.title()
    return f"{artist} - {title}"


def main():
    parser = argparse.ArgumentParser(
        description="Scrape ExpressFM playlist and output songs for Spotify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
      Scrape today's playlist, save to songs.txt

  %(prog)s -o expresfm.txt
      Save to custom file

  %(prog)s --limit 50
      Get only the 50 most recent songs

  %(prog)s --no-headless
      Show browser window (for debugging)

Workflow:
  1. %(prog)s -o songs.txt
  2. python spotify_playlist.py songs.txt "ExpressFM Playlist"
"""
    )
    parser.add_argument(
        "-o", "--output",
        default="songs.txt",
        help="Output file (default: songs.txt)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (for debugging)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of songs (0 = all)"
    )
    args = parser.parse_args()

    # Scrape the playlist
    songs = scrape_playlist(headless=not args.no_headless)

    # Remove duplicates while preserving order
    seen = set()
    unique_songs = []
    for song in songs:
        key = (song[0].lower(), song[1].lower())
        if key not in seen:
            seen.add(key)
            unique_songs.append(song)

    print(f"Found {len(unique_songs)} unique songs")

    # Apply limit if specified
    if args.limit > 0:
        unique_songs = unique_songs[:args.limit]

    # Format and write to file
    with open(args.output, "w", encoding="utf-8") as f:
        for artist, title in unique_songs:
            line = format_song(artist, title)
            f.write(line + "\n")

    print(f"Saved {len(unique_songs)} songs to {args.output}")


if __name__ == "__main__":
    main()
