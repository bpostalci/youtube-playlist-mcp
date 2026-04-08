"""OAuth 2.0 authentication for YouTube Data API v3.

Handles the initial browser-based consent flow, token persistence,
and automatic refresh on subsequent runs.
"""

import json
import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKEN_DIR = Path.home() / ".config" / "youtube-playlist-mcp"
TOKEN_PATH = TOKEN_DIR / "token.json"


def get_client_secret_path() -> Path:
    """Resolve the path to client_secret.json.

    Checks YOUTUBE_CLIENT_SECRET env var first, then falls back to
    ./client_secret.json in the current working directory.
    """
    env_path = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if env_path:
        return Path(env_path)
    return Path("client_secret.json")


def load_credentials() -> Credentials | None:
    """Load saved credentials from disk and refresh if expired.

    Returns None if no saved token exists or the token is invalid
    and cannot be refreshed.
    """
    if not TOKEN_PATH.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
            logger.info("Token refreshed successfully")
            return creds
        except Exception:
            logger.warning("Token refresh failed — re-authentication required")
            return None

    return None


def authenticate_interactive() -> Credentials:
    """Run the full OAuth browser flow and persist the token.

    This opens a browser window for the user to grant consent.
    Should only be needed once; subsequent calls use load_credentials().
    """
    secret_path = get_client_secret_path()
    if not secret_path.exists():
        raise FileNotFoundError(
            f"Client secret file not found at {secret_path}. "
            "Download it from Google Cloud Console and set YOUTUBE_CLIENT_SECRET "
            "or place it in the current directory as client_secret.json."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    logger.info("Authentication successful — token saved to %s", TOKEN_PATH)
    return creds


def get_credentials() -> Credentials:
    """Get valid credentials, loading from disk or raising if unavailable.

    For non-interactive use (the MCP server). If no valid token exists,
    raises RuntimeError directing the user to run authenticate first.
    """
    creds = load_credentials()
    if creds is None:
        raise RuntimeError(
            "No valid YouTube credentials found. "
            "Run 'uv run authenticate' first to complete the OAuth flow."
        )
    return creds


def _save_credentials(creds: Credentials) -> None:
    """Persist credentials to disk."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
