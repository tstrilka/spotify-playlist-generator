#!/usr/bin/env python3
"""
Scrape played songs from Radio 1 program schedule.

Fetches the program page and extracts artist/title for each song.
Supports DJ-based filtering with auto-classification based on genre preferences.
Outputs in format compatible with spotify_playlist.py.
"""

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright

URL = "https://www.radio1.cz/program/"
DJ_STATS_FILE = "radio1_dj_stats.json"

# Genre classification for DJ auto-scoring
PREFERRED_GENRES = [
    "rock", "indie", "alternative", "post-punk", "shoegaze", "grunge",
    "punk", "new wave", "brit", "garage", "psychedelic", "progressive",
    "electronic", "synth", "dream pop", "noise", "experimental"
]
AVOIDED_GENRES = [
    "rap", "hip hop", "hip-hop", "trap", "drill", "grime", "r&b", "rnb",
    "reggaeton", "urban", "gangsta"
]


@dataclass
class DJStats:
    """Track genre statistics for a DJ."""
    name: str
    songs_count: int = 0
    genre_counts: dict = field(default_factory=dict)
    preferred_score: int = 0
    avoided_score: int = 0

    def add_genres(self, genres: list[str]):
        """Add genre counts from a song."""
        for genre in genres:
            genre_lower = genre.lower()
            self.genre_counts[genre_lower] = self.genre_counts.get(genre_lower, 0) + 1
            # Update scores
            for pref in PREFERRED_GENRES:
                if pref in genre_lower:
                    self.preferred_score += 1
                    break
            for avoid in AVOIDED_GENRES:
                if avoid in genre_lower:
                    self.avoided_score += 1
                    break

    @property
    def score(self) -> float:
        """Calculate DJ score: positive = good, negative = bad."""
        if self.songs_count == 0:
            return 0.0
        return (self.preferred_score - self.avoided_score) / self.songs_count

    @property
    def classification(self) -> str:
        """Classify DJ based on score."""
        if self.score > 0.1:
            return "preferred"
        elif self.score < -0.1:
            return "avoided"
        return "neutral"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "songs_count": self.songs_count,
            "genre_counts": self.genre_counts,
            "preferred_score": self.preferred_score,
            "avoided_score": self.avoided_score,
            "score": self.score,
            "classification": self.classification,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DJStats":
        stats = cls(name=data["name"])
        stats.songs_count = data.get("songs_count", 0)
        stats.genre_counts = data.get("genre_counts", {})
        stats.preferred_score = data.get("preferred_score", 0)
        stats.avoided_score = data.get("avoided_score", 0)
        return stats


def load_dj_stats() -> dict[str, DJStats]:
    """Load DJ statistics from file."""
    if os.path.exists(DJ_STATS_FILE):
        try:
            with open(DJ_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {name: DJStats.from_dict(d) for name, d in data.items()}
        except:
            pass
    return {}


def save_dj_stats(stats: dict[str, DJStats]):
    """Save DJ statistics to file."""
    data = {name: s.to_dict() for name, s in stats.items()}
    with open(DJ_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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


def extract_dj_name(text: str) -> str | None:
    """
    Extract DJ name from a time slot header line.

    Examples:
    - "06.00 - 09.00 Antonín Kocábek" -> "Antonín Kocábek"
    - "Novinky na alternativní scéně / Josef Sedloň" -> "Josef Sedloň"
    """
    # Pattern: time range followed by DJ name
    time_pattern = r'^\d{1,2}[.:]\d{2}\s*[-–]\s*\d{1,2}[.:]\d{2}\s*(.+)$'
    match = re.match(time_pattern, text.strip())
    if match:
        name = match.group(1).strip()
        # Clean up: remove "show name / " prefix
        if '/' in name:
            name = name.split('/')[-1].strip()
        if len(name) > 2 and len(name) < 50:
            return name

    # Also check for standalone names in <strong> or similar (captured as plain text)
    # Skip obvious non-names
    skip_patterns = [
        r'^\d', r'^https?:', r'^Zobrazit', r'[-–]', r'@', r'\.cz',
        r'^(Singly|Alba|EPs|Singles|Albums):', r'^[🛒\s]+$'
    ]
    for pattern in skip_patterns:
        if re.search(pattern, text.strip()):
            return None

    return None


def scrape_program(headless: bool = True) -> list[tuple[str, str, str]]:
    """
    Scrape the Radio 1 program page.

    Returns list of (artist, title, dj_name) tuples.
    """
    songs = []
    current_dj = "Unknown"

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

        # Strategy: Find all h3/h4 headers (time slots with DJ names) and their associated song lists
        # Radio1 structure: h4 with time+DJ, followed by ul/li with songs

        # First, try to get structured data from article sections
        articles = page.query_selector_all("article, .program-item, [class*='program']")

        if articles:
            print(f"Found {len(articles)} program sections")
            for article in articles:
                try:
                    # Look for DJ name in headers
                    headers = article.query_selector_all("h3, h4, h5, strong")
                    for header in headers:
                        header_text = header.text_content() or ""
                        dj = extract_dj_name(header_text)
                        if dj:
                            current_dj = dj
                            print(f"  DJ: {current_dj}")
                            break

                    # Get all song lines from this section
                    items = article.query_selector_all("li")
                    for item in items:
                        text = item.text_content() or ""
                        result = parse_song_line(text)
                        if result:
                            songs.append((result[0], result[1], current_dj))
                except:
                    continue

        # Fallback: parse full page text line by line
        if not songs:
            print("Trying full page text extraction with DJ tracking...")
            try:
                full_text = page.text_content("body") or ""
                lines = full_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Check if this is a DJ header
                    dj = extract_dj_name(line)
                    if dj:
                        current_dj = dj
                        continue

                    # Try to parse as song
                    result = parse_song_line(line)
                    if result:
                        songs.append((result[0], result[1], current_dj))
            except:
                pass

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


def analyze_dj_genres(songs: list[tuple[str, str, str]], dj_stats: dict[str, DJStats]) -> dict[str, DJStats]:
    """
    Analyze genres for songs using Spotify API and update DJ statistics.

    Returns updated DJ stats dictionary.
    """
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        from dotenv import load_dotenv

        load_dotenv()

        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

        if not client_id or not client_secret:
            print("Warning: Spotify credentials not set. Skipping genre analysis.")
            print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET for DJ auto-classification.")
            return dj_stats

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="",
            open_browser=False,
        )

        sp = spotipy.Spotify(auth_manager=auth_manager)
        print("\nAnalyzing genres for DJ classification...")

        # Group songs by DJ
        songs_by_dj: dict[str, list[tuple[str, str]]] = {}
        for artist, title, dj in songs:
            if dj not in songs_by_dj:
                songs_by_dj[dj] = []
            songs_by_dj[dj].append((artist, title))

        for dj_name, dj_songs in songs_by_dj.items():
            if dj_name not in dj_stats:
                dj_stats[dj_name] = DJStats(name=dj_name)

            stats = dj_stats[dj_name]
            print(f"  Analyzing {dj_name} ({len(dj_songs)} songs)...")

            for artist, title in dj_songs:
                try:
                    # Search for the track
                    query = f"{artist} {title}"
                    results = sp.search(q=query, type="track", limit=1)
                    tracks = results.get("tracks", {}).get("items", [])

                    if tracks:
                        track = tracks[0]
                        artist_id = track["artists"][0]["id"]

                        # Get artist genres
                        artist_info = sp.artist(artist_id)
                        genres = artist_info.get("genres", [])

                        stats.songs_count += 1
                        stats.add_genres(genres)
                except Exception as e:
                    # Skip songs that fail
                    continue

        return dj_stats

    except ImportError:
        print("Warning: spotipy not installed. Skipping genre analysis.")
        return dj_stats
    except Exception as e:
        print(f"Warning: Genre analysis failed: {e}")
        return dj_stats


def print_dj_stats(stats: dict[str, DJStats]):
    """Print DJ statistics in a readable format."""
    print("\n" + "=" * 60)
    print("DJ CLASSIFICATION RESULTS")
    print("=" * 60)

    # Sort by score (preferred first, then neutral, then avoided)
    sorted_djs = sorted(stats.values(), key=lambda x: -x.score)

    for s in sorted_djs:
        status = {
            "preferred": "✓ PREFERRED",
            "avoided": "✗ AVOIDED",
            "neutral": "○ neutral"
        }.get(s.classification, "?")

        print(f"\n{status}: {s.name}")
        print(f"  Songs analyzed: {s.songs_count}")
        print(f"  Score: {s.score:.2f} (preferred: {s.preferred_score}, avoided: {s.avoided_score})")

        if s.genre_counts:
            top_genres = sorted(s.genre_counts.items(), key=lambda x: -x[1])[:5]
            genres_str = ", ".join(f"{g}({c})" for g, c in top_genres)
            print(f"  Top genres: {genres_str}")

    print("\n" + "=" * 60)


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

  %(prog)s --filter-djs
      Filter songs using DJ auto-classification (excludes avoided DJs)

  %(prog)s --analyze-djs
      Analyze DJ genres without filtering (builds DJ profile database)

  %(prog)s --show-djs
      Show current DJ classifications from saved data

  %(prog)s --limit 50
      Get only 50 songs

  %(prog)s --no-headless
      Show browser window (for debugging)

DJ Auto-Classification:
  The system learns DJ preferences by analyzing genres of songs they play:
  - Preferred genres: rock, indie, alternative, post-punk, shoegaze, etc.
  - Avoided genres: rap, hip hop, trap, drill, r&b, etc.

  DJs are classified as:
  - PREFERRED: Score > 0.1 (plays mostly rock/indie)
  - AVOIDED: Score < -0.1 (plays mostly rap/hip-hop)
  - neutral: Between -0.1 and 0.1

Workflow:
  1. %(prog)s --analyze-djs    # First run: learn DJ preferences
  2. %(prog)s --filter-djs     # Subsequent runs: filter by learned preferences
  3. python spotify_playlist.py songs.txt "Radio 1 Playlist"
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
    parser.add_argument(
        "--analyze-djs",
        action="store_true",
        help="Analyze DJ genres using Spotify API (builds DJ classification database)"
    )
    parser.add_argument(
        "--filter-djs",
        action="store_true",
        help="Filter out songs from avoided DJs (uses saved classifications)"
    )
    parser.add_argument(
        "--show-djs",
        action="store_true",
        help="Show current DJ classifications and exit"
    )
    parser.add_argument(
        "--include-neutral",
        action="store_true",
        help="When filtering, include songs from neutral DJs (default: only preferred)"
    )
    parser.add_argument(
        "--top-djs",
        type=int,
        default=0,
        help="Only include songs from top N DJs by score (e.g., --top-djs 6)"
    )
    args = parser.parse_args()

    # Load existing DJ stats
    dj_stats = load_dj_stats()

    # Show DJs mode
    if args.show_djs:
        if not dj_stats:
            print("No DJ data found. Run with --analyze-djs first to build the database.")
        else:
            print_dj_stats(dj_stats)
        return

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

    # Show DJ distribution
    dj_counts: dict[str, int] = {}
    for artist, title, dj in unique_songs:
        dj_counts[dj] = dj_counts.get(dj, 0) + 1
    print("\nSongs by DJ:")
    for dj, count in sorted(dj_counts.items(), key=lambda x: -x[1]):
        print(f"  {dj}: {count} songs")

    # Analyze DJs if requested
    if args.analyze_djs:
        dj_stats = analyze_dj_genres(unique_songs, dj_stats)
        save_dj_stats(dj_stats)
        print_dj_stats(dj_stats)
        print(f"\nDJ stats saved to {DJ_STATS_FILE}")

    # Filter by top N DJs if requested
    if args.top_djs > 0:
        if not dj_stats:
            print("\nWarning: No DJ classification data. Run with --analyze-djs first.")
            print("Proceeding without filtering...")
        else:
            # Get top N DJs by score
            sorted_djs = sorted(dj_stats.values(), key=lambda x: -x.score)
            top_dj_names = {s.name for s in sorted_djs[:args.top_djs]}

            print(f"\nTop {args.top_djs} DJs by score:")
            for s in sorted_djs[:args.top_djs]:
                print(f"  {s.name}: {s.score:.2f}")

            original_count = len(unique_songs)
            unique_songs = [(a, t, d) for a, t, d in unique_songs if d in top_dj_names]
            print(f"\nFiltered: {original_count} -> {len(unique_songs)} songs")

    # Filter by DJ classification if requested
    elif args.filter_djs:
        if not dj_stats:
            print("\nWarning: No DJ classification data. Run with --analyze-djs first.")
            print("Proceeding without filtering...")
        else:
            original_count = len(unique_songs)
            filtered_songs = []

            for artist, title, dj in unique_songs:
                if dj in dj_stats:
                    classification = dj_stats[dj].classification
                    if classification == "preferred":
                        filtered_songs.append((artist, title, dj))
                    elif classification == "neutral" and args.include_neutral:
                        filtered_songs.append((artist, title, dj))
                    # else: avoided, skip
                else:
                    # Unknown DJ - include if --include-neutral
                    if args.include_neutral:
                        filtered_songs.append((artist, title, dj))

            unique_songs = filtered_songs
            print(f"\nFiltered: {original_count} -> {len(unique_songs)} songs")
            print("(Excluded songs from avoided DJs)")

    # Apply limit if specified
    if args.limit > 0:
        unique_songs = unique_songs[:args.limit]

    # Format and write to file
    with open(args.output, "w", encoding="utf-8") as f:
        for artist, title, *rest in unique_songs:
            line = format_song(artist, title)
            f.write(line + "\n")

    print(f"\nSaved {len(unique_songs)} songs to {args.output}")


if __name__ == "__main__":
    main()
