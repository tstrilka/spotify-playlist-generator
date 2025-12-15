# Spotify Playlist Generator

Create Spotify playlists from a text file or scrape songs from ExpressFM radio.

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

Create a `.env` file (don't commit this to git):
```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install firefox
```

## Usage

### Create Playlist from File

```bash
python spotify_playlist.py songs.txt "My Playlist"
```

Options:
- `-d, --description`: Add a playlist description
- `--private`: Make the playlist private
- `-x, --exclude-genres`: Comma-separated genres to exclude

Examples:
```bash
# Basic playlist
python spotify_playlist.py songs.txt "My Playlist"

# Private playlist with description
python spotify_playlist.py songs.txt "Chill Vibes" -d "Relaxing music" --private

# Exclude rap and hip-hop
python spotify_playlist.py songs.txt "Rock Playlist" -x "rap,hip hop,trap"
```

### Scrape ExpressFM Radio

Scrape today's playlist from ExpressFM and create a Spotify playlist:

```bash
# Scrape songs from ExpressFM
python scrape_expresfm.py -o songs.txt

# Create Spotify playlist (excluding rap/hip-hop)
python spotify_playlist.py songs.txt "ExpressFM Playlist" -x "rap,hip hop"
```

Scraper options:
- `-o, --output`: Output file (default: songs.txt)
- `--limit`: Limit number of songs (0 = all)
- `--no-headless`: Show browser window (for debugging)

### First Run

On first run, Firefox will open for Spotify login. After authorizing, copy the redirect URL from the browser and paste it into the terminal.

## Input File Format

One song per line in the format `Artist - Track Name`:

```
Daft Punk - Get Lucky
The Weeknd - Blinding Lights
Tame Impala - The Less I Know The Better
```

## File Structure

```
spotify-playlist-generator/
├── spotify_playlist.py   # Main script - creates Spotify playlists
├── scrape_expresfm.py    # Scrapes ExpressFM radio playlist
├── requirements.txt      # Python dependencies
├── songs.txt             # Example song list
├── .env                  # Spotify credentials (not in git)
└── README.md
```
