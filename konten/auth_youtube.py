"""
auth_youtube.py — One-time OAuth2 setup for YouTube upload.
Run ONCE to generate token.json, then never again.

Run: python auth_youtube.py
"""

import json
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("[ERROR] pip install google-auth google-auth-oauthlib google-api-python-client --break-system-packages")
    exit(1)

SCOPES          = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS  = Path(__file__).parent / "client_secrets.json"
TOKEN_FILE      = Path(__file__).parent / "token.json"


def authenticate():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(f"[ERROR] client_secrets.json not found at {CLIENT_SECRETS}")
                exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS), SCOPES
            )
            # Port 0 = random available port (works on Termux)
            creds = flow.run_local_server(port=0, open_browser=False)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"[OK] Token saved → {TOKEN_FILE}")

    print(f"[OK] Authenticated as: {creds.token[:20]}...")
    return creds


if __name__ == "__main__":
    print("YouTube OAuth2 Setup")
    print("="*40)
    print("1. A URL will appear below")
    print("2. Open it in your browser")
    print("3. Login with your YouTube account")
    print("4. Copy the authorization code back here")
    print("="*40)
    authenticate()
    print("\n[DONE] token.json created. You can now use worker_upload.py")

