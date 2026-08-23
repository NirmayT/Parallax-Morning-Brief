"""Read labeled Gmail messages using one token with read and send scopes."""
import os
import config
import utils
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def credentials():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.GMAIL_SCOPES)
        except Exception:
            creds = None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not os.path.exists(config.CREDENTIALS_FILE):
            utils.log("[GMAIL] Missing credentials.json.")
            return None
        flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, config.GMAIL_SCOPES)
        creds = flow.run_local_server(port=0)
    with open(config.TOKEN_FILE, "w", encoding="utf-8") as handle:
        handle.write(creds.to_json())
    return creds


def service():
    creds = credentials()
    return None if creds is None else build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_messages_since(start):
    api = service()
    if api is None:
        return []
    query = f'label:{config.GMAIL_LABEL} after:{utils.to_epoch(start)}'
    utils.log(f"[GMAIL] Query: {query}")
    items, request = [], api.users().messages().list(userId="me", q=query)
    while request:
        response = request.execute()
        items.extend(response.get("messages", []))
        request = api.users().messages().list_next(request, response)
    utils.log(f"[GMAIL] Found {len(items)} message(s).")
    output = []
    for item in items:
        try:
            output.append(api.users().messages().get(userId="me", id=item["id"], format="full").execute())
        except Exception as exc:
            utils.log(f"[GMAIL] Message {item.get('id')} failed: {exc}")
    return output
