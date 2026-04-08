"""Thin wrapper around the YouTube Data API v3 client.

All methods return plain dicts — no raw API response objects leak out.
Handles common error cases (quota exceeded, not found) with clear exceptions.
"""

import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


class YouTubeAPIError(Exception):
    """Raised for YouTube API errors with a user-friendly message."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


def _handle_http_error(e: HttpError) -> None:
    """Convert HttpError into a YouTubeAPIError with a clear message."""
    status = e.resp.status
    if status == 403:
        raise YouTubeAPIError(
            "YouTube API quota exceeded (10,000 units/day default). "
            "Wait until midnight Pacific Time or request a quota increase "
            "in the Google Cloud Console.",
            status_code=403,
        ) from e
    if status == 404:
        raise YouTubeAPIError(
            "Resource not found — the playlist, video, or item ID may be invalid.",
            status_code=404,
        ) from e
    raise YouTubeAPIError(
        f"YouTube API error (HTTP {status}): {e.reason}",
        status_code=status,
    ) from e


class YouTubeClient:
    """Wrapper around the YouTube Data API v3."""

    def __init__(self, credentials: Credentials):
        self._service = build(
            API_SERVICE_NAME,
            API_VERSION,
            credentials=credentials,
            cache_discovery=False,
        )

    def list_playlists(self, max_results: int = 50) -> list[dict]:
        """List the authenticated user's playlists."""
        try:
            items = []
            request = self._service.playlists().list(
                part="snippet,status,contentDetails",
                mine=True,
                maxResults=min(max_results, 50),
            )
            while request and len(items) < max_results:
                response = request.execute()
                for item in response.get("items", []):
                    items.append({
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"]["description"],
                        "privacy": item["status"]["privacyStatus"],
                        "item_count": item["contentDetails"]["itemCount"],
                        "published_at": item["snippet"]["publishedAt"],
                    })
                request = self._service.playlists().list_next(request, response)
            return items[:max_results]
        except HttpError as e:
            _handle_http_error(e)

    def get_playlist(self, playlist_id: str, max_items: int = 25) -> dict:
        """Get playlist details plus the first N items."""
        try:
            response = self._service.playlists().list(
                part="snippet,status,contentDetails",
                id=playlist_id,
            ).execute()

            if not response.get("items"):
                raise YouTubeAPIError(
                    f"Playlist {playlist_id} not found.", status_code=404
                )

            pl = response["items"][0]
            items = self.list_playlist_items(playlist_id, max_results=max_items)

            return {
                "id": pl["id"],
                "title": pl["snippet"]["title"],
                "description": pl["snippet"]["description"],
                "privacy": pl["status"]["privacyStatus"],
                "item_count": pl["contentDetails"]["itemCount"],
                "published_at": pl["snippet"]["publishedAt"],
                "channel_title": pl["snippet"]["channelTitle"],
                "items": items,
            }
        except HttpError as e:
            _handle_http_error(e)

    def list_playlist_items(
        self, playlist_id: str, max_results: int = 50
    ) -> list[dict]:
        """List items in a playlist with pagination."""
        try:
            items = []
            request = self._service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=min(max_results, 50),
            )
            while request and len(items) < max_results:
                response = request.execute()
                for item in response.get("items", []):
                    snippet = item["snippet"]
                    items.append({
                        "playlist_item_id": item["id"],
                        "video_id": snippet["resourceId"]["videoId"],
                        "title": snippet["title"],
                        "channel_title": snippet.get("videoOwnerChannelTitle", ""),
                        "position": snippet["position"],
                        "added_at": snippet.get("publishedAt", ""),
                    })
                request = self._service.playlistItems().list_next(request, response)
            return items[:max_results]
        except HttpError as e:
            _handle_http_error(e)

    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy: str = "private",
    ) -> dict:
        """Create a new playlist. Returns the created playlist's details."""
        try:
            response = self._service.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": title, "description": description},
                    "status": {"privacyStatus": privacy},
                },
            ).execute()

            return {
                "id": response["id"],
                "title": response["snippet"]["title"],
                "description": response["snippet"]["description"],
                "privacy": response["status"]["privacyStatus"],
            }
        except HttpError as e:
            _handle_http_error(e)

    def update_playlist(
        self,
        playlist_id: str,
        title: str | None = None,
        description: str | None = None,
        privacy: str | None = None,
    ) -> dict:
        """Update a playlist's metadata. Only provided fields are changed."""
        try:
            # Fetch current state to preserve unchanged fields
            current = self._service.playlists().list(
                part="snippet,status", id=playlist_id
            ).execute()

            if not current.get("items"):
                raise YouTubeAPIError(
                    f"Playlist {playlist_id} not found.", status_code=404
                )

            item = current["items"][0]
            snippet = item["snippet"]
            status = item["status"]

            body: dict = {
                "id": playlist_id,
                "snippet": {
                    "title": title if title is not None else snippet["title"],
                    "description": (
                        description
                        if description is not None
                        else snippet["description"]
                    ),
                },
                "status": {
                    "privacyStatus": (
                        privacy if privacy is not None else status["privacyStatus"]
                    ),
                },
            }

            response = self._service.playlists().update(
                part="snippet,status", body=body
            ).execute()

            return {
                "id": response["id"],
                "title": response["snippet"]["title"],
                "description": response["snippet"]["description"],
                "privacy": response["status"]["privacyStatus"],
            }
        except HttpError as e:
            _handle_http_error(e)

    def delete_playlist(self, playlist_id: str) -> dict:
        """Delete a playlist. Returns confirmation."""
        try:
            self._service.playlists().delete(id=playlist_id).execute()
            return {"deleted": True, "playlist_id": playlist_id}
        except HttpError as e:
            _handle_http_error(e)

    def add_video_to_playlist(
        self,
        playlist_id: str,
        video_id: str,
        position: int | None = None,
    ) -> dict:
        """Add a video to a playlist at an optional position."""
        try:
            body: dict = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                },
            }
            if position is not None:
                body["snippet"]["position"] = position

            response = self._service.playlistItems().insert(
                part="snippet", body=body
            ).execute()

            snippet = response["snippet"]
            return {
                "playlist_item_id": response["id"],
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "position": snippet["position"],
            }
        except HttpError as e:
            _handle_http_error(e)

    def remove_video_from_playlist(self, playlist_item_id: str) -> dict:
        """Remove a video from a playlist by its playlist item ID."""
        try:
            self._service.playlistItems().delete(id=playlist_item_id).execute()
            return {"deleted": True, "playlist_item_id": playlist_item_id}
        except HttpError as e:
            _handle_http_error(e)

    def move_video_in_playlist(
        self, playlist_item_id: str, new_position: int
    ) -> dict:
        """Move a video to a new position within its playlist."""
        try:
            # Fetch the current item to get required fields
            current = self._service.playlistItems().list(
                part="snippet", id=playlist_item_id
            ).execute()

            if not current.get("items"):
                raise YouTubeAPIError(
                    f"Playlist item {playlist_item_id} not found.", status_code=404
                )

            item = current["items"][0]
            snippet = item["snippet"]

            response = self._service.playlistItems().update(
                part="snippet",
                body={
                    "id": playlist_item_id,
                    "snippet": {
                        "playlistId": snippet["playlistId"],
                        "resourceId": snippet["resourceId"],
                        "position": new_position,
                    },
                },
            ).execute()

            return {
                "playlist_item_id": response["id"],
                "video_id": response["snippet"]["resourceId"]["videoId"],
                "title": response["snippet"]["title"],
                "new_position": response["snippet"]["position"],
            }
        except HttpError as e:
            _handle_http_error(e)

    def search_videos(self, query: str, max_results: int = 10) -> list[dict]:
        """Search YouTube for videos. Returns video id, title, and channel."""
        try:
            response = self._service.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=min(max_results, 50),
            ).execute()

            return [
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "description": item["snippet"]["description"],
                    "published_at": item["snippet"]["publishedAt"],
                }
                for item in response.get("items", [])
            ]
        except HttpError as e:
            _handle_http_error(e)
