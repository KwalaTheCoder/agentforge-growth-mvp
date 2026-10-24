"""Explicitly approved, single-recipient Gmail API delivery. No bulk sends."""
import json
import os
import re
import hashlib
from pathlib import Path
from email.message import EmailMessage
from email.utils import parseaddr
from base64 import urlsafe_b64encode

SCOPE = ["https://www.googleapis.com/auth/gmail.send"]
PRIVATE = Path(__file__).resolve().parent / ".agentforge_private"


def _dependencies():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError("Install Gmail dependencies: pip install -r requirements_gmail.txt") from e
    return Credentials, InstalledAppFlow, Request, build


def _token_path():
    return PRIVATE / "gmail_token.json"


def connect(client_secrets_path):
    Credentials, InstalledAppFlow, Request, build = _dependencies()
    p = Path(client_secrets_path).expanduser().resolve()
    if not p.is_file():
        raise ValueError("OAuth client JSON file not found")
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(p), scopes=SCOPE)
    creds = flow.run_local_server(host="localhost", port=0, open_browser=True,
                                  authorization_prompt_message="Open this URL to authorize Gmail: {url}")
    _token_path().write_text(creds.to_json(), encoding="utf-8")
    try: os.chmod(_token_path(), 0o600)
    except OSError: pass
    return True


def _service():
    Credentials, InstalledAppFlow, Request, build = _dependencies()
    if not _token_path().exists():
        raise RuntimeError("Connect Gmail first")
    creds = Credentials.from_authorized_user_file(str(_token_path()), SCOPE)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _token_path().write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError("Gmail authorization expired. Reconnect.")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def validate_recipient(value):
    name, addr = parseaddr(value.strip())
    if name or addr != value.strip() or not re.fullmatch(r"[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+", addr):
        raise ValueError("Enter one valid recipient email address")
    return addr


def build_message(to, subject, body):
    to = validate_recipient(to)
    if not subject.strip() or not body.strip():
        raise ValueError("Subject and message body are required")
    if any(c in subject for c in "\r\n"):
        raise ValueError("Invalid subject")
    msg=EmailMessage()
    msg["To"]=to
    msg["Subject"]=subject.strip()
    msg.set_content(body)
    return {"raw":urlsafe_b64encode(msg.as_bytes()).decode("ascii")}


def fingerprint(to, subject, body):
    return hashlib.sha256(json.dumps([to.strip().lower(),subject.strip(),body],ensure_ascii=False).encode()).hexdigest()


def send_once(to, subject, body, *, approved, consent_basis, log_path=None):
    if not approved:
        raise PermissionError("Explicit send approval required")
    if not consent_basis.strip():
        raise PermissionError("Record a verified lawful/appropriate contact basis")
    payload=build_message(to,subject,body)
    digest=fingerprint(to,subject,body)
    log=Path(log_path) if log_path else PRIVATE/'sent_log.jsonl'
    log.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if log.exists():
        for line in log.read_text(encoding='utf-8').splitlines():
            try:
                if json.loads(line).get('fingerprint')==digest:
                    raise ValueError('This exact message was already sent; duplicate blocked')
            except json.JSONDecodeError: pass
    result=_service().users().messages().send(userId='me',body=payload).execute()
    with log.open('a',encoding='utf-8') as f:
        f.write(json.dumps({'fingerprint':digest,'to':to,'subject':subject,'gmail_id':result.get('id'),
                            'consent_basis':consent_basis.strip()},ensure_ascii=False)+'\n')
    return result
