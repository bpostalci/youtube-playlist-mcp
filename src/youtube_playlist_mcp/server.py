"""YouTube Playlist MCP Server.

Exposes YouTube Data API v3 playlist operations as MCP tools
via FastMCP. All tools return clean JSON-serializable dicts.
"""

import logging
import sys

from fastmcp import FastMCP

from youtube_playlist_mcp.auth import get_credentials
from youtube_playlist_mcp.youtube import YouTubeClient, YouTubeAPIError

# Log to stderr only — stdout is reserved for MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP("YouTube Playlist Manager")

_client: YouTubeClient | None = None


def _get_client() -> YouTubeClient:
    """Lazy-init the YouTube client with cached credentials."""
    global _client
    if _client is None:
        creds = get_credentials()
        _client = YouTubeClient(creds)
        logger.info("YouTube client initialized")
    return _client


def _error_response(e: Exception) -> dict:
    """Format an exception as a tool error response."""
    if isinstance(e, YouTubeAPIError):
        return {"error": str(e), "status_code": e.status_code}
    return {"error": str(e)}


@mcp.tool()
def list_playlists(max_results: int = 50) -> list[dict] | dict:
    """List your YouTube playlists.

    Returns a list of playlists with fields: id, title, description,
    privacy (public/private/unlisted), item_count, published_at.

    Args:
        max_results: Maximum number of playlists to return (default 50).
    """
    try:
        return _get_client().list_playlists(max_results=max_results)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def get_playlist(playlist_id: str, max_items: int = 25) -> dict:
    """Get detailed info about a specific playlist including its items.

    Returns: id, title, description, privacy, item_count, published_at,
    channel_title, and an items list (each with playlist_item_id, video_id,
    title, channel_title, position, added_at).

    Args:
        playlist_id: The YouTube playlist ID (e.g. "PLxxxxxxxx").
        max_items: Max number of items to include (default 25).
    """
    try:
        return _get_client().get_playlist(playlist_id, max_items=max_items)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def list_playlist_items(playlist_id: str, max_results: int = 50) -> list[dict] | dict:
    """List videos in a playlist with pagination.

    Returns a list of items, each with: playlist_item_id, video_id,
    title, channel_title, position, added_at.

    Args:
        playlist_id: The YouTube playlist ID.
        max_results: Maximum items to return (default 50, max 50 per page).
    """
    try:
        return _get_client().list_playlist_items(playlist_id, max_results=max_results)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def create_playlist(
    title: str, description: str = "", privacy: str = "private"
) -> dict:
    """Create a new YouTube playlist.

    Returns the created playlist: id, title, description, privacy.
    Costs 50 quota units.

    Args:
        title: Playlist title.
        description: Playlist description (default empty).
        privacy: One of "public", "private", or "unlisted" (default "private").
    """
    try:
        return _get_client().create_playlist(title, description, privacy)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def update_playlist(
    playlist_id: str,
    title: str | None = None,
    description: str | None = None,
    privacy: str | None = None,
) -> dict:
    """Update a playlist's title, description, or privacy status.

    Only the provided fields are changed; others remain as-is.
    Returns the updated playlist: id, title, description, privacy.
    Costs 50 quota units.

    Args:
        playlist_id: The playlist ID to update.
        title: New title (optional).
        description: New description (optional).
        privacy: New privacy status — "public", "private", or "unlisted" (optional).
    """
    try:
        return _get_client().update_playlist(playlist_id, title, description, privacy)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def delete_playlist(playlist_id: str, confirm: bool = False) -> dict:
    """Delete a YouTube playlist. This action is irreversible.

    You MUST set confirm=True to actually delete. Returns {"deleted": true}
    on success. Costs 50 quota units.

    Args:
        playlist_id: The playlist ID to delete.
        confirm: Safety flag — must be True to proceed with deletion.
    """
    if not confirm:
        return {
            "error": "Deletion not confirmed. Set confirm=True to delete this playlist. "
            "This action is irreversible."
        }
    try:
        return _get_client().delete_playlist(playlist_id)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def add_video_to_playlist(
    playlist_id: str, video_id: str, position: int | None = None
) -> dict:
    """Add a video to a playlist.

    Returns the new item: playlist_item_id, video_id, title, position.
    Costs 50 quota units.

    Args:
        playlist_id: Target playlist ID.
        video_id: YouTube video ID to add (e.g. "dQw4w9WgXcQ").
        position: 0-based position to insert at (optional, appends to end if omitted).
    """
    try:
        return _get_client().add_video_to_playlist(playlist_id, video_id, position)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def remove_video_from_playlist(playlist_item_id: str) -> dict:
    """Remove a video from a playlist.

    Use list_playlist_items to find the playlist_item_id first.
    Returns {"deleted": true} on success. Costs 50 quota units.

    Args:
        playlist_item_id: The playlist item ID (NOT the video ID).
            Get this from list_playlist_items.
    """
    try:
        return _get_client().remove_video_from_playlist(playlist_item_id)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def move_video_in_playlist(playlist_item_id: str, new_position: int) -> dict:
    """Move a video to a different position within its playlist.

    Returns the updated item: playlist_item_id, video_id, title, new_position.
    Costs 50 quota units.

    Args:
        playlist_item_id: The playlist item ID to move.
        new_position: 0-based target position.
    """
    try:
        return _get_client().move_video_in_playlist(playlist_item_id, new_position)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


@mcp.tool()
def search_videos(query: str, max_results: int = 10) -> list[dict] | dict:
    """Search YouTube for videos.

    Returns a list of results, each with: video_id, title, channel_title,
    description, published_at. Use the video_id to add videos to playlists.
    Costs 100 quota units.

    Args:
        query: Search query string.
        max_results: Maximum results to return (default 10, max 50).
    """
    try:
        return _get_client().search_videos(query, max_results=max_results)
    except (YouTubeAPIError, RuntimeError) as e:
        return _error_response(e)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
