#!/usr/bin/env python3
"""
Scrape played songs from Radio 1 program schedule.

Fetches the program page and extracts artist/title for each song.
Outputs in format compatible with spotify_playlist.py.
"""

import argparse
import re
from playwright.sync_api import sync_playwright

URL = "https://www.radio1.cz/program/"


def handle_consent(page):
    """Handle cookie consent dialog if present."""
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


def parse_song_line(line: str) -> tuple[str, str] | None:
    """
    Parse a song line in format "Artist - Title".

    Returns (artist, title) tuple or None if parsing fails.
    """
    line = line.strip()
    if not line or len(line) < 5:
        return None

    # Skip lines that are clearly not songs
    skip_patterns = [
        r'^\d{1,2}[:.]\d{2}',  # Time stamps like "06:00" or "6.00"
        r'^https?://',  # URLs
        r'^\d+\s*$',  # Just numbers
        r'[{}]',  # CSS/code artifacts
        r'^Zobrazit',  # UI text
        r'^[🛒\s]+$',  # Emoji-only lines
        r'Stroke|Fill|Width',  # SVG/CSS
    ]
    for pattern in skip_patterns:
        if re.search(pattern, line):
            return None

    # Look for " - " separator (most common format)
    if ' - ' in line:
        parts = line.split(' - ', 1)
        if len(parts) == 2:
            artist = parts[0].strip()
            title = parts[1].strip()

            # Validate - both parts should have reasonable length
            if len(artist) < 2 or len(title) < 2:
                return None

            # Skip if artist or title contains only emojis or special chars
            if re.match(r'^[\W\s]+$', artist) or re.match(r'^[\W\s]+$', title):
                return None

            # Skip if too long (likely concatenated garbage)
            if len(artist) > 100 or len(title) > 150:
                return None

            return (artist, title)

    return None


def scrape_program(headless: bool = True) -> list[tuple[str, str]]:
    """
    Scrape the Radio 1 program page.

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
                page.wait_for_timeout(2000)
                break
            page.wait_for_timeout(1000)

        # Get page content and look for song patterns
        # Songs are typically in list items or paragraphs within program blocks

        # Try to find program/playlist sections
        section_selectors = [
            ".program-item",
            ".playlist",
            ".tracklist",
            ".song-list",
            "article",
            ".program__item",
            "[class*='program']",
            "[class*='playlist']",
        ]

        sections = []
        for selector in section_selectors:
            try:
                found = page.query_selector_all(selector)
                if found:
                    sections.extend(found)
                    print(f"Found {len(found)} sections with selector: {selector}")
            except:
                continue

        # Extract text from sections and parse song lines
        processed_texts = set()

        for section in sections:
            try:
                text = section.text_content() or ""
                if text in processed_texts:
                    continue
                processed_texts.add(text)

                # Split into lines and try to parse each
                lines = text.split('\n')
                for line in lines:
                    result = parse_song_line(line)
                    if result:
                        songs.append(result)
            except:
                continue

        # If no songs found via sections, try getting all text and parsing
        if not songs:
            print("Trying full page text extraction...")
            try:
                full_text = page.text_content("body") or ""
                lines = full_text.split('\n')
                for line in lines:
                    result = parse_song_line(line)
                    if result:
                        songs.append(result)
            except:
                pass

        # Also try looking for specific list items that might contain songs
        if not songs:
            print("Trying list item extraction...")
            list_items = page.query_selector_all("li, p")
            for item in list_items:
                try:
                    text = item.text_content() or ""
                    result = parse_song_line(text)
                    if result:
                        songs.append(result)
                except:
                    continue

        # Debug: save page if no songs found
        if not songs:
            print("Warning: No songs extracted. Page structure may have changed.")
            try:
                content = page.content()
                with open("radio1_debug.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("Saved page HTML to radio1_debug.html for debugging")
            except:
                pass

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
        description="Scrape Radio 1 program and output songs for Spotify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
      Scrape program songs, save to songs.txt

  %(prog)s -o radio1.txt
      Save to custom file

  %(prog)s --limit 50
      Get only 50 songs

  %(prog)s --no-headless
      Show browser window (for debugging)

Workflow:
  1. %(prog)s -o songs.txt
  2. python spotify_playlist.py songs.txt "Radio 1 Playlist"
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

    # Scrape the program
    songs = scrape_program(headless=not args.no_headless)

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
