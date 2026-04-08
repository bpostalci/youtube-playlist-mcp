"""One-time CLI script to complete the YouTube OAuth flow.

Run this before using the MCP server:
    uv run authenticate
"""

import sys

from youtube_playlist_mcp.auth import authenticate_interactive, load_credentials


def main() -> None:
    existing = load_credentials()
    if existing:
        print("Already authenticated — valid token found.")
        print("To re-authenticate, delete ~/.config/youtube-playlist-mcp/token.json")
        sys.exit(0)

    print("Starting YouTube OAuth flow...")
    print("A browser window will open for you to grant access.\n")

    try:
        authenticate_interactive()
        print("\nAuthentication successful! You can now use the MCP server.")
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAuthentication failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
