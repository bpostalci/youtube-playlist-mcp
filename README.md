# YouTube Playlist MCP Server

MCP server for managing YouTube and YouTube Music playlists from Claude Desktop via the YouTube Data API v3.

## Setup

### 1. Get YouTube API credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **YouTube Data API v3** (APIs & Services → Library)
3. Create **OAuth client ID** credentials (APIs & Services → Credentials → Desktop app)
4. Download the JSON and save it as `client_secret.json` in this project root
5. Configure the OAuth consent screen if prompted (add your Google account as a test user)

### 2. Install and authenticate

```bash
uv sync
uv run authenticate
```

### 3. Add to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-playlists": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/youtube-playlist-mcp",
        "run", "youtube-playlist-mcp"
      ]
    }
  }
}
```

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop after editing.

## Tools

| Tool | Description | Quota |
|------|-------------|-------|
| `list_playlists` | List your playlists | 1 |
| `get_playlist` | Playlist details + items | 3 |
| `list_playlist_items` | Videos in a playlist | 1 |
| `create_playlist` | Create a playlist | 50 |
| `update_playlist` | Update title/description/privacy | 50 |
| `delete_playlist` | Delete a playlist (requires confirm flag) | 50 |
| `add_video_to_playlist` | Add a video to a playlist | 50 |
| `remove_video_from_playlist` | Remove a video from a playlist | 50 |
| `move_video_in_playlist` | Reorder a video in a playlist | 50 |
| `search_videos` | Search YouTube | 100 |

## Quota

YouTube Data API default quota is **10,000 units/day**. Reads are cheap (1-3 units), writes cost 50, search costs 100.
