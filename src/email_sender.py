"""Save every edition locally, then optionally send through Gmail."""
import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config
import utils
import gmail_client


def save_local(subject, plain, html):
    utils.ensure_dirs()
    stamp = utils.now_local().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(config.OUTPUT_DIR, f"brief_{stamp}.html")
    txt_path = os.path.join(config.OUTPUT_DIR, f"brief_{stamp}.txt")
    open(html_path, "w", encoding="utf-8").write(html)
    open(txt_path, "w", encoding="utf-8").write(plain)
    utils.log(f"[SENDER] Saved local copy: {html_path}")
    return html_path


def deliver(subject, plain, html, dry_run=False):
    save_local(subject, plain, html)
    if dry_run:
        return False
    try:
        api = gmail_client.service()
        message = MIMEMultipart("alternative")
        message["Subject"], message["From"], message["To"] = subject, config.SENDER_EMAIL, config.RECIPIENT_EMAIL
        message.attach(MIMEText(plain, "plain", "utf-8"))
        message.attach(MIMEText(html, "html", "utf-8"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        api.users().messages().send(userId="me", body={"raw": raw}).execute()
        utils.log("[SENDER] Email sent via Gmail API.")
        return True
    except Exception as exc:
        utils.log(f"[SENDER] Gmail send failed: {exc}")
        return False
