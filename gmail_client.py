from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import smtplib


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

# --- EXAMPLE RUN ---
#if __name__ == "__main__":
#    send_gmail_email(
#        to_email="recipient_address@example.com",
#        subject="Secure Email via Azure Vault",
#        body_content="This password was pulled securely from Azure Key Vault at runtime."
#    )