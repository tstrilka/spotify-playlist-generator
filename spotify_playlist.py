#!/usr/bin/env python3
"""
Spotify Playlist Generator

Reads songs from a text file and creates a Spotify playlist.
Format: One song per line as "Artist - Track Name"
"""

import os
import sys
import argparse
import webbrowser
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPE = "playlist-modify-public playlist-modify-private"


def read_songs(filepath: str) -> list[str]:
    """Read songs from a text file, one per line."""
    with open(filepath, "r", encoding="utf-8") as f:
        songs = [line.strip() for line in f if line.strip()]
    return songs


def get_artist_genres(sp: spotipy.Spotify, artist_id: str) -> list[str]:
    """Get genres for an artist."""
    try:
        artist = sp.artist(artist_id)
        return [g.lower() for g in artist.get("genres", [])]
    except:
        return []


def search_track(
    sp: spotipy.Spotify, query: str, exclude_genres: list[str] | None = None
) -> str | None:
    """Search for a track and return its URI if found."""
    try:
        results = sp.search(q=query, type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if tracks:
            track = tracks[0]
            artist_name = track['artists'][0]['name']
            track_name = track['name']

            # Check genre filter
            if exclude_genres:
                artist_id = track['artists'][0]['id']
                genres = get_artist_genres(sp, artist_id)
                for genre in genres:
                    for excluded in exclude_genres:
                        if excluded in genre:
                            print(f"  Skipped (genre '{genre}'): {artist_name} - {track_name}")
                            return None

            print(f"  Found: {artist_name} - {track_name}")
            return track["uri"]
        else:
            print(f"  Not found: {query}")
            return None
    except Exception as e:
        print(f"  Error searching '{query}': {e}")
        return None


def create_playlist(
    sp: spotipy.Spotify, user_id: str, name: str, description: str = "", public: bool = True
) -> str:
    """Create a new playlist and return its ID."""
    playlist = sp.user_playlist_create(
        user=user_id, name=name, public=public, description=description
    )
    return playlist["id"]


def add_tracks_to_playlist(sp: spotipy.Spotify, playlist_id: str, track_uris: list[str]):
    """Add tracks to a playlist in batches of 100."""
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i : i + 100]
        sp.playlist_add_items(playlist_id, batch)


def main():
    parser = argparse.ArgumentParser(
        description="Create a Spotify playlist from a text file of songs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s songs.txt "My Playlist"
      Create a public playlist from songs.txt

  %(prog)s songs.txt "Chill Vibes" -d "Relaxing music" --private
      Create a private playlist with description

  %(prog)s songs.txt "Rock Playlist" -x "rap,hip hop,trap"
      Create playlist excluding rap/hip-hop genres

Input file format (one song per line):
  Artist - Track Name
  Daft Punk - Get Lucky
  The Weeknd - Blinding Lights
"""
    )
    parser.add_argument("songs_file", help="Path to text file with songs (one per line: Artist - Track)")
    parser.add_argument("playlist_name", help="Name for the new playlist")
    parser.add_argument("--description", "-d", default="", help="Playlist description")
    parser.add_argument("--private", action="store_true", help="Make playlist private")
    parser.add_argument(
        "--exclude-genres", "-x",
        default="",
        help="Comma-separated genres to exclude (e.g., 'rap,hip hop')"
    )
    args = parser.parse_args()

    # Parse excluded genres
    exclude_genres = [g.strip().lower() for g in args.exclude_genres.split(",") if g.strip()]

    # Check for credentials
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        print("Error: Missing Spotify credentials.")
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")
        print("See README.md for setup instructions.")
        sys.exit(1)

    # Authenticate with Spotify
    print("Authenticating with Spotify...")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        open_browser=False,
    )

    # Check if we already have a valid token
    token_info = auth_manager.get_cached_token()
    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        print(f"Opening Firefox for authorization...")
        webbrowser.get("firefox").open(auth_url)

        print("\nAfter authorizing, paste the redirect URL here:")
        response_url = input().strip()
        code = auth_manager.parse_response_code(response_url)
        auth_manager.get_access_token(code)

    sp = spotipy.Spotify(auth_manager=auth_manager)

    user = sp.current_user()
    user_id = user["id"]
    print(f"Logged in as: {user['display_name']} ({user_id})")

    # Read songs from file
    print(f"\nReading songs from {args.songs_file}...")
    songs = read_songs(args.songs_file)
    print(f"Found {len(songs)} songs to search\n")

    # Search for each track
    print("Searching for tracks...")
    if exclude_genres:
        print(f"Excluding genres: {', '.join(exclude_genres)}\n")
    track_uris = []
    for song in songs:
        uri = search_track(sp, song, exclude_genres=exclude_genres or None)
        if uri:
            track_uris.append(uri)

    print(f"\nFound {len(track_uris)} of {len(songs)} tracks")

    if not track_uris:
        print("No tracks found. Exiting.")
        sys.exit(1)

    # Create playlist
    print(f"\nCreating playlist '{args.playlist_name}'...")
    playlist_id = create_playlist(
        sp, user_id, args.playlist_name, args.description, public=not args.private
    )

    # Add tracks
    print("Adding tracks to playlist...")
    add_tracks_to_playlist(sp, playlist_id, track_uris)

    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"\nPlaylist created successfully!")
    print(f"URL: {playlist_url}")


if __name__ == "__main__":
    main()
