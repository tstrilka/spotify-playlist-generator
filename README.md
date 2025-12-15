# Spotify Playlist Generator

Create Spotify playlists from a simple text file.

## Setup

### 1. Create Spotify Developer App

1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in:
   - App name: `Playlist Generator` (or anything you like)
   - App description: `Create playlists from text files`
   - Redirect URI: `http://127.0.0.1:8888/callback`
5. Check the Web API checkbox
6. Click "Save"
7. Click "Settings" to view your **Client ID** and **Client Secret**

### 2. Set Environment Variables

```bash
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
```

Or create a `.env` file (don't commit this to git):
```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Create Your Song List

Create a text file with one song per line in the format `Artist - Track Name`:

```
Daft Punk - Get Lucky
The Weeknd - Blinding Lights
Tame Impala - The Less I Know The Better
```

### Run the Script

```bash
python spotify_playlist.py songs.txt "My Playlist"
```

Options:
- `--description` or `-d`: Add a playlist description
- `--private`: Make the playlist private

Example:
```bash
python spotify_playlist.py songs.txt "Summer Vibes" -d "My summer playlist" --private
```

### First Run

On first run, your browser will open for Spotify login. After authorizing, you'll be redirected to `127.0.0.1:8888/callback`. The script will capture the token automatically.

## File Structure

```
spotify-playlist-generator/
├── spotify_playlist.py   # Main script
├── requirements.txt      # Python dependencies
├── songs.txt            # Example song list
└── README.md            # This file
```
