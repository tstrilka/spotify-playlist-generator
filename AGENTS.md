# Spotify Playlist Generator

## Overview
Python CLI tool that creates Spotify playlists from a text file of songs. Can also scrape songs from ExpressFM radio station. Supports genre filtering to exclude unwanted music styles.

## Tech Stack
- Python 3
- spotipy (Spotify Web API wrapper)
- python-dotenv (environment variable management)
- playwright (web scraping with headless Firefox)

## Project Structure
```
spotify_playlist.py   # Main script - handles auth, search, playlist creation
scrape_expresfm.py    # Scrapes ExpressFM playlist page
requirements.txt      # Dependencies
songs.txt             # Input file (one song per line: "Artist - Track Name")
.env                  # Spotify API credentials (not in git)
.cache                # Spotify auth token cache (not in git)
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

### Scraper options
```bash
python scrape_expresfm.py -o songs.txt --limit 50  # Limit to 50 songs
python scrape_expresfm.py --no-headless            # Show browser (debug)
```

## Input Format
```
Artist - Track Name
Daft Punk - Get Lucky
The Weeknd - Blinding Lights
```

## Genre Filtering
The `-x` option checks each artist's genres on Spotify and skips tracks matching excluded genres. Genre matching is partial (e.g., "rap" matches "trap", "rap", "german rap").
