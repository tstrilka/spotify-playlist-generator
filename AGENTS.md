# Spotify Playlist Generator

## Overview
Python CLI tool that creates Spotify playlists from a text file of songs.

## Tech Stack
- Python 3
- spotipy (Spotify Web API wrapper)
- python-dotenv (environment variable management)

## Project Structure
```
spotify_playlist.py   # Main script - handles auth, search, playlist creation
requirements.txt      # Dependencies
songs.txt            # Input file (one song per line: "Artist - Track Name")
.env                 # Spotify API credentials (not in git)
.cache               # Spotify auth token cache (not in git)
```

## Key Functions
- `read_songs()` - Reads song list from text file
- `search_track()` - Searches Spotify API for a track, returns URI
- `create_playlist()` - Creates new playlist for authenticated user
- `add_tracks_to_playlist()` - Adds tracks in batches of 100

## Authentication
Uses OAuth2 via SpotifyOAuth. Opens Firefox for user authorization. Token cached in `.cache` file.

## Environment Variables
- `SPOTIFY_CLIENT_ID` - From Spotify Developer Dashboard
- `SPOTIFY_CLIENT_SECRET` - From Spotify Developer Dashboard
- `SPOTIFY_REDIRECT_URI` - Optional, defaults to `http://127.0.0.1:8888/callback`

## Usage
```bash
python spotify_playlist.py <songs_file> <playlist_name> [--description "desc"] [--private]
```

## Input Format
```
Artist - Track Name
Daft Punk - Get Lucky
The Weeknd - Blinding Lights
```
