from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import smtplib
import imaplib
import email
from email.header import decode_header, make_header


# --- AZURE & GMAIL CONFIGURATION ---
SENDER_EMAIL = "manuchadha25@gmail.com"
VAULT_URL = "https://claude-demo-vault.vault.azure.net/"
SECRET_NAME = "GMAIL-APP-PASSWORD"  # The name you gave the secret in Azure

# Note: You WILL need to import these Azure packages (just like your Jira code)

def get_gmail_password_from_vault() -> str:
    """Fetches the 16-character Gmail App Password from Azure Key Vault."""
    print("Fetching Gmail App Password from Azure Key Vault...")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=VAULT_URL, credential=credential)
    retrieved_secret = client.get_secret(SECRET_NAME)
    return retrieved_secret.value.strip()

def send_gmail_email(to_email: str, subject: str, body_content: str):
    """Sends an email using a Gmail account with credentials from Azure Vault."""
    try:
        # 1. Dynamically retrieve the app password at runtime
        app_password = get_gmail_password_from_vault()
    except Exception as e:
        print(f"Failed to retrieve secret from Azure Key Vault: {e}")
        return

    # 2. Standard SMTP Setup
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_content, 'plain'))

    try:
        print("Connecting to Google's mail server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  
        
        server.login(SENDER_EMAIL, app_password)
        
        print("Sending email...")
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"Success! Gmail successfully sent to {to_email}.")
        
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
    finally:
        server.quit()

def _extract_text(msg: email.message.Message) -> str:
    """Returns the plain-text body of a message (first text/plain part)."""
    if msg.is_multipart():
        for part in msg.walk():
            if (part.get_content_type() == "text/plain"
                    and "attachment" not in str(part.get("Content-Disposition", ""))):
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def read_gmail_inbox(query: str = "ALL", limit: int = 10, mailbox: str = "INBOX") -> list[dict]:
    """Reads recent emails over IMAP using the same Azure Vault app password.

    `query` is an IMAP search string, e.g. 'UNSEEN', 'FROM "a@b.com"', 'SUBJECT "invoice"'.
    Returns up to `limit` messages, newest first.
    """
    app_password = get_gmail_password_from_vault()
    results = []
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as imap:
        imap.login(SENDER_EMAIL, app_password)
        imap.select(mailbox, readonly=True)  # readonly: don't mark messages as read
        status, data = imap.search(None, query)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {query}")
        ids = data[0].split()[-limit:][::-1]
        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            results.append({
                "id": msg_id.decode(),
                "from": str(make_header(decode_header(msg.get("From", "")))),
                "subject": str(make_header(decode_header(msg.get("Subject", "")))),
                "date": msg.get("Date", ""),
                "body": _extract_text(msg),
            })
    return results


# --- EXAMPLE RUN ---
#if __name__ == "__main__":
#    for m in read_gmail_inbox("UNSEEN", limit=5):
#        print(m["date"], m["from"], "-", m["subject"])
#
# --- SEND EXAMPLE ---
#if __name__ == "__main__":
#    send_gmail_email(
#        to_email="recipient_address@example.com",
#        subject="Secure Email via Azure Vault",
#        body_content="This password was pulled securely from Azure Key Vault at runtime."
#    )