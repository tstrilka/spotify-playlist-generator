# Spotify Playlist Generator

## Overview
Python CLI tool that creates Spotify playlists from a text file of songs. Can also scrape songs from Czech radio stations (ExpressFM, Radio 1). Supports genre filtering to exclude unwanted music styles.

Radio 1 scraper includes DJ auto-classification: learns each DJ's music taste via Spotify genre analysis and filters songs to only include preferred DJs (rock/indie) while excluding avoided ones (rap/hip-hop).

## Tech Stack
- Python 3
- spotipy (Spotify Web API wrapper)
- python-dotenv (environment variable management)
- playwright (web scraping with headless Firefox)

## Project Structure
```
spotify_playlist.py      # Main script - handles auth, search, playlist creation
scrape_expresfm.py       # Scrapes ExpressFM playlist page
scrape_radio1.py         # Scrapes Radio 1 program schedule with DJ filtering
requirements.txt         # Dependencies
songs.txt                # Input file (one song per line: "Artist - Track Name")
radio1_dj_stats.json     # DJ classification database (auto-generated)
.env                     # Spotify API credentials (not in git)
.cache                   # Spotify auth token cache (not in git)
```

## Key Functions

### spotify_playlist.py
- `read_songs()` - Reads song list from text file
- `get_artist_genres()` - Fetches artist genres from Spotify API
- `search_track()` - Searches Spotify API for a track, returns URI, supports genre filtering
- `create_playlist()` - Creates new playlist for authenticated user
- `add_tracks_to_playlist()` - Adds tracks in batches of 100

### scrape_expresfm.py
- `handle_consent()` - Handles Seznam.cz cookie consent dialog
- `scrape_playlist()` - Scrapes ExpressFM playlist, returns (artist, title) tuples
- `format_song()` - Formats song for Spotify search

### scrape_radio1.py
- `handle_consent()` - Handles cookie consent dialog
- `parse_song_line()` - Parses "Artist - Title" format from text
- `extract_dj_name()` - Extracts DJ name from time slot headers
- `scrape_program()` - Scrapes Radio 1 program page (https://www.radio1.cz/program/), returns (artist, title, dj_name) tuples
- `format_song()` - Formats song for Spotify search
- `DJStats` - Dataclass tracking DJ genre statistics and classification score
- `load_dj_stats()` / `save_dj_stats()` - Persist DJ classifications to JSON
- `analyze_dj_genres()` - Queries Spotify API for artist genres, updates DJ scores
- `print_dj_stats()` - Displays DJ classification results

## Authentication
Uses OAuth2 via SpotifyOAuth. Opens Firefox for user authorization. Token cached in `.cache` file.

## Environment Variables
- `SPOTIFY_CLIENT_ID` - From Spotify Developer Dashboard
- `SPOTIFY_CLIENT_SECRET` - From Spotify Developer Dashboard
- `SPOTIFY_REDIRECT_URI` - Optional, defaults to `http://127.0.0.1:8888/callback`

## Usage

### Create playlist from file
```bash
python spotify_playlist.py <songs_file> <playlist_name> [options]
```

Options:
- `-d, --description` - Playlist description
- `--private` - Make playlist private
- `-x, --exclude-genres` - Comma-separated genres to exclude (e.g., "rap,hip hop")

### Scrape ExpressFM and create playlist
```bash
python scrape_expresfm.py -o songs.txt
python spotify_playlist.py songs.txt "ExpressFM Playlist" -x "rap,hip hop"
```

### Scrape Radio 1 and create playlist
```bash
python scrape_radio1.py -o songs.txt
python spotify_playlist.py songs.txt "Radio 1 Playlist"
```

### Radio 1 DJ filtering workflow
```bash
# Step 1: Analyze DJ genres (builds classification database)
python scrape_radio1.py --analyze-djs

# Step 2: View DJ classifications
python scrape_radio1.py --show-djs

# Step 3: Filter by preferred DJs only
python scrape_radio1.py --filter-djs

# Or: Filter by top N DJs by score
python scrape_radio1.py --top-djs 6

# Include neutral DJs too (not just preferred)
python scrape_radio1.py --filter-djs --include-neutral
```

### Scraper options (both scrapers)
```bash
python scrape_expresfm.py -o songs.txt --limit 50  # Limit to 50 songs
python scrape_expresfm.py --no-headless            # Show browser (debug)
python scrape_radio1.py -o songs.txt --limit 100   # Radio 1 with limit
```

## Input Format
```
Artist - Track Name
Daft Punk - Get Lucky
The Weeknd - Blinding Lights
```

## Genre Filtering
The `-x` option checks each artist's genres on Spotify and skips tracks matching excluded genres. Genre matching is partial (e.g., "rap" matches "trap", "rap", "german rap").

## DJ Auto-Classification (Radio 1)

The system learns DJ music preferences by analyzing Spotify genres of songs they play.

### Scoring
- **Preferred genres**: rock, indie, alternative, post-punk, shoegaze, grunge, punk, new wave, electronic, synth, dream pop, experimental
- **Avoided genres**: rap, hip hop, trap, drill, grime, r&b, reggaeton, urban

Each song's artist genres are checked against these lists. DJ score = (preferred_count - avoided_count) / songs_count

### Classifications
- **PREFERRED** (score > 0.1): Plays mostly rock/indie - songs included by default
- **AVOIDED** (score < -0.1): Plays mostly rap/hip-hop - songs excluded
- **neutral** (between): Mixed taste - excluded by default, include with `--include-neutral`

### Data Persistence
DJ statistics are saved to `radio1_dj_stats.json` and accumulate over multiple runs of `--analyze-djs`.
