# Agentic Application Development: Real Enterprise Systems Guide

## Systems Available on Free / Solo Plans

| System | Category | Free Plan Details |
|--------|----------|-------------------|
| **HubSpot** | CRM | Free CRM forever (contacts, deals, pipeline) |
| **Salesforce** | CRM | Developer Edition — free, full API access |
| **Gmail API** | Email | Free via Google Cloud (generous quota) |
| **SendGrid** | Email | 100 emails/day free forever |
| **Slack** | Messaging | Free tier + full Bot/API access |
| **Supabase** | Database (Postgres) | Free tier — 500MB, REST + realtime |
| **Airtable** | Database / Spreadsheet | Free tier — 1,200 records/base, API access |
| **Notion** | Docs / Knowledge Base | Free personal plan, full API access |
| **Jira (Cloud)** | Project Management | Free for ≤10 users, full REST API |
| **Linear** | Project Management | Free for individuals, API access |
| **GitHub** | Code / Issues | Free, full REST + GraphQL API |
| **Google Calendar** | Scheduling | Free via Google Cloud |
| **Twilio** | SMS / Voice | $15 free trial credit |
| **Freshdesk** | Support Ticketing | Free for 2 agents |
| **Stripe** | Payments | Free to integrate; pay per transaction |
| **Cloudflare D1** | Edge Database | Free tier — 5GB, 100k writes/day |

---

## Use Case 1: AI Customer Support Resolution Agent

**What it does:** Handles inbound support tickets end-to-end — looks up the customer, reads their history, resolves known issues, and escalates if needed.

**Systems involved:** Freshdesk → HubSpot CRM → Supabase → Gmail → Slack

**Flow:**
```
New ticket arrives in Freshdesk
  → lookup_customer(email) in HubSpot
  → query_order_history(customer_id) in Supabase
  → classify_issue() [LLM step]
  → if known issue: send_resolution_email() via Gmail
  → if complex: post_to_slack(#support-escalations) with full context
  → update_ticket_status() in Freshdesk
```

**Tools your agent needs:**
```python
tools = [
    {"name": "get_ticket",         "description": "Fetch ticket from Freshdesk by ID"},
    {"name": "lookup_crm_contact", "description": "Find customer in HubSpot by email"},
    {"name": "query_order_history","description": "Fetch orders from Supabase DB"},
    {"name": "send_email",         "description": "Send resolution email via SendGrid"},
    {"name": "post_slack_message", "description": "Post escalation to Slack channel"},
    {"name": "close_ticket",       "description": "Mark Freshdesk ticket resolved"},
]
```

---

## Use Case 2: AI Sales Pipeline Assistant

**What it does:** Monitors new inbound leads, enriches them, creates CRM records, assigns to sales reps, and books intro meetings.

**Systems involved:** Gmail → HubSpot CRM → Google Calendar → Slack → Notion

**Flow:**
```
New lead email arrives in Gmail
  → extract_lead_details() [LLM parse]
  → create_contact() in HubSpot
  → create_deal() in HubSpot pipeline
  → find_available_slot() in Google Calendar
  → send_booking_email() via Gmail
  → post_slack_message() to #new-leads with summary
  → create_notion_page() with lead research brief
```

---

## Use Case 3: AI Engineering Sprint Manager

**What it does:** Takes a product requirement doc from Notion, breaks it into tasks, creates Jira issues, assigns them based on GitHub contributor history, and posts the sprint plan to Slack.

**Systems involved:** Notion → GitHub → Jira → Slack

**Flow:**
```
PRD created in Notion
  → read_notion_page(page_id)
  → decompose_into_tasks() [LLM step]
  → get_github_contributors() from repo
  → match_tasks_to_engineers() [LLM step]
  → create_jira_issues() in bulk
  → post_sprint_plan() to Slack #engineering
```

---

## Use Case 4: AI Invoice & Payment Follow-up Agent

**What it does:** Tracks overdue invoices in Airtable, sends personalised chaser emails, logs payment confirmations, and updates records automatically.

**Systems involved:** Airtable → Stripe → Gmail/SendGrid → Slack

**Flow:**
```
Daily trigger
  → list_overdue_invoices() from Airtable (filter: due_date < today, status = unpaid)
  → for each invoice:
      → check_stripe_payment_status(invoice_id)
      → if still unpaid: send_chaser_email() via SendGrid
      → if paid: update_airtable_record(status = paid)
  → post_daily_summary() to Slack #finance
```

---

## Use Case 5: AI Incident Response Agent

**What it does:** When a production alert fires, the agent investigates, queries logs, assesses severity, notifies the right people, and creates a Jira incident ticket.

**Systems involved:** Slack (alert source) → Supabase → GitHub → Jira → Slack (notifications)

**Flow:**
```
Alert message in Slack #alerts
  → parse_alert(message)
  → query_error_logs(service, time_window) from Supabase
  → get_recent_commits(repo) from GitHub
  → assess_severity() [LLM step]
  → if P1: page_oncall_engineer() via Slack DM
  → create_incident_ticket() in Jira
  → post_incident_thread() in Slack #incidents
```

---

## Step-by-Step Connection Guides

---

### 1. HubSpot CRM

**Get API Key:**
1. Go to https://app.hubspot.com → Settings → Integrations → Private Apps
2. Click **Create a private app** → give it a name
3. Under **Scopes**, select: `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.objects.deals.read`, `crm.objects.deals.write`
4. Click **Create app** → copy the **Access Token**

**Python implementation:**
```python
import requests

HUBSPOT_TOKEN = "your_access_token"
BASE = "https://api.hubapi.com"

def lookup_crm_contact(email: str) -> dict:
    resp = requests.get(
        f"{BASE}/crm/v3/objects/contacts/search",
        headers={"Authorization": f"Bearer {HUBSPOT_TOKEN}"},
        json={"filterGroups": [{"filters": [
            {"propertyName": "email", "operator": "EQ", "value": email}
        ]}]}
    )
    results = resp.json().get("results", [])
    return results[0] if results else {}

def create_deal(contact_id: str, deal_name: str, amount: float) -> dict:
    resp = requests.post(
        f"{BASE}/crm/v3/objects/deals",
        headers={"Authorization": f"Bearer {HUBSPOT_TOKEN}"},
        json={"properties": {
            "dealname": deal_name,
            "amount": str(amount),
            "dealstage": "appointmentscheduled"
        }}
    )
    return resp.json()
```

---

### 2. Supabase (PostgreSQL)

**Setup:**
1. Go to https://supabase.com → Create a new project (free)
2. Wait for provisioning → go to **Project Settings → API**
3. Copy your **Project URL** and **anon/public key**
4. Go to **SQL Editor** → create your tables

**Python implementation:**
```python
# pip install supabase
from supabase import create_client

SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your_anon_key"

client = create_client(SUPABASE_URL, SUPABASE_KEY)

def query_order_history(customer_id: str) -> list:
    resp = client.table("orders") \
        .select("*") \
        .eq("customer_id", customer_id) \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
    return resp.data

def insert_incident_log(service: str, severity: str, message: str) -> dict:
    resp = client.table("incidents").insert({
        "service": service,
        "severity": severity,
        "message": message
    }).execute()
    return resp.data[0]
```

---

### 3. Slack Bot

**Setup:**
1. Go to https://api.slack.com/apps → **Create New App → From Scratch**
2. Name it, pick your workspace
3. Go to **OAuth & Permissions → Bot Token Scopes**, add:
   - `chat:write`, `channels:read`, `channels:history`, `im:write`
4. Click **Install to Workspace** → copy the **Bot User OAuth Token**
5. Invite your bot to channels: `/invite @your-bot-name`

**Python implementation:**
```python
# pip install slack-sdk
from slack_sdk import WebClient

SLACK_TOKEN = "xoxb-your-bot-token"
client = WebClient(token=SLACK_TOKEN)

def post_slack_message(channel: str, text: str, blocks: list = None) -> dict:
    resp = client.chat_postMessage(
        channel=channel,
        text=text,
        blocks=blocks  # optional: rich Block Kit formatting
    )
    return resp.data

def send_dm(user_email: str, message: str) -> dict:
    # Look up user by email first
    user = client.users_lookupByEmail(email=user_email)
    user_id = user["user"]["id"]
    channel = client.conversations_open(users=user_id)["channel"]["id"]
    return client.chat_postMessage(channel=channel, text=message).data
```

---

### 4. Gmail API

**Setup:**
1. Go to https://console.cloud.google.com → Create a project
2. Enable the **Gmail API** under APIs & Services
3. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID** (Desktop app)
4. Download the `credentials.json`
5. Run the auth flow once locally to get `token.json`

**Python implementation:**
```python
# pip install google-auth google-auth-oauthlib google-api-python-client
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.message import EmailMessage

SCOPES = ["https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

def send_email(to: str, subject: str, body: str) -> dict:
    service = get_gmail_service()
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": encoded}
    ).execute()
    return result

def read_latest_emails(max_results: int = 10) -> list:
    service = get_gmail_service()
    result = service.users().messages().list(
        userId="me", maxResults=max_results
    ).execute()
    return result.get("messages", [])
```

---

### 5. Jira Cloud

**Setup:**
1. Sign up at https://www.atlassian.com/software/jira — free for ≤10 users
2. Go to **https://id.atlassian.com/manage-profile/security/api-tokens**
3. Click **Create API token** → copy it
4. Your base URL is: `https://your-domain.atlassian.net`

**Python implementation:**
```python
# pip install requests
import requests
from requests.auth import HTTPBasicAuth

JIRA_BASE = "https://your-domain.atlassian.net"
JIRA_EMAIL = "you@example.com"
JIRA_TOKEN = "your_api_token"
AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

def create_jira_issue(project_key: str, summary: str, description: str,
                       issue_type: str = "Task") -> dict:
    resp = requests.post(
        f"{JIRA_BASE}/rest/api/3/issue",
        headers=HEADERS, auth=AUTH,
        json={"fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {"type": "doc", "version": 1,
                            "content": [{"type": "paragraph",
                                         "content": [{"type": "text", "text": description}]}]},
            "issuetype": {"name": issue_type}
        }}
    )
    return resp.json()

def get_open_issues(project_key: str) -> list:
    jql = f"project = {project_key} AND status != Done ORDER BY created DESC"
    resp = requests.get(
        f"{JIRA_BASE}/rest/api/3/search",
        headers=HEADERS, auth=AUTH,
        params={"jql": jql, "maxResults": 50}
    )
    return resp.json().get("issues", [])
```

---

### 6. Notion

**Setup:**
1. Go to https://www.notion.com/my-integrations → **New integration**
2. Give it a name and select your workspace
3. Copy the **Internal Integration Secret**
4. In Notion, open any page → **... menu → Connections → add your integration**

**Python implementation:**
```python
# pip install notion-client
from notion_client import Client

NOTION_TOKEN = "secret_your_token"
notion = Client(auth=NOTION_TOKEN)

def read_notion_page(page_id: str) -> str:
    blocks = notion.blocks.children.list(block_id=page_id)
    text_parts = []
    for block in blocks["results"]:
        btype = block["type"]
        if btype in ["paragraph", "heading_1", "heading_2", "bulleted_list_item"]:
            rich_text = block[btype].get("rich_text", [])
            text_parts.extend([t["plain_text"] for t in rich_text])
    return "\n".join(text_parts)

def create_notion_page(parent_page_id: str, title: str, content: str) -> dict:
    return notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={"title": {"title": [{"text": {"content": title}}]}},
        children=[{"object": "block", "type": "paragraph",
                   "paragraph": {"rich_text": [{"text": {"content": content}}]}}]
    )
```

---

### 7. Airtable

**Setup:**
1. Sign up at https://airtable.com (free: 1,200 records/base)
2. Go to https://airtable.com/account → **API** → generate a **Personal Access Token**
3. Grant scopes: `data.records:read`, `data.records:write`
4. Find your Base ID from any base URL: `https://airtable.com/appXXXXXXX/...`

**Python implementation:**
```python
# pip install pyairtable
from pyairtable import Api

AIRTABLE_TOKEN = "patXXXXXXXX"
AIRTABLE_BASE_ID = "appXXXXXXXX"

api = Api(AIRTABLE_TOKEN)

def list_overdue_invoices() -> list:
    table = api.table(AIRTABLE_BASE_ID, "Invoices")
    records = table.all(formula="AND({Status}='Unpaid', IS_BEFORE({DueDate}, TODAY()))")
    return [r["fields"] for r in records]

def update_invoice_status(record_id: str, status: str) -> dict:
    table = api.table(AIRTABLE_BASE_ID, "Invoices")
    return table.update(record_id, {"Status": status})
```

---

### 8. GitHub API

**Setup:**
1. Go to https://github.com/settings/tokens → **Fine-grained personal access tokens**
2. Create a token with: `repo` (read), `issues` (read/write)

**Python implementation:**
```python
# pip install PyGithub
from github import Github

GITHUB_TOKEN = "ghp_your_token"
g = Github(GITHUB_TOKEN)

def get_recent_commits(repo_name: str, limit: int = 20) -> list:
    repo = g.get_repo(repo_name)  # e.g. "org/repo"
    commits = list(repo.get_commits()[:limit])
    return [{"sha": c.sha[:7], "message": c.commit.message,
             "author": c.commit.author.name} for c in commits]

def create_github_issue(repo_name: str, title: str, body: str,
                         labels: list = None) -> dict:
    repo = g.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body, labels=labels or [])
    return {"id": issue.number, "url": issue.html_url}
```

---

## Wiring It All Together: The Agent Loop

```python
import anthropic

client = anthropic.Anthropic()

# Register ALL your real tools
TOOLS = [
    {"name": "lookup_crm_contact",    "description": "Find customer in HubSpot by email",
     "input_schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}},
    {"name": "query_order_history",   "description": "Fetch customer orders from database",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "send_email",            "description": "Send an email via Gmail",
     "input_schema": {"type": "object", "properties": {
         "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}
     }, "required": ["to", "subject", "body"]}},
    {"name": "post_slack_message",    "description": "Post a message to a Slack channel",
     "input_schema": {"type": "object", "properties": {
         "channel": {"type": "string"}, "text": {"type": "string"}
     }, "required": ["channel", "text"]}},
    {"name": "create_jira_issue",     "description": "Create a Jira ticket",
     "input_schema": {"type": "object", "properties": {
         "project_key": {"type": "string"}, "summary": {"type": "string"}, "description": {"type": "string"}
     }, "required": ["project_key", "summary", "description"]}},
]

# Route tool calls to real implementations
def execute_tool(name: str, input_data: dict):
    if name == "lookup_crm_contact":
        return lookup_crm_contact(input_data["email"])
    elif name == "query_order_history":
        return query_order_history(input_data["customer_id"])
    elif name == "send_email":
        return send_email(input_data["to"], input_data["subject"], input_data["body"])
    elif name == "post_slack_message":
        return post_slack_message(input_data["channel"], input_data["text"])
    elif name == "create_jira_issue":
        return create_jira_issue(input_data["project_key"],
                                  input_data["summary"], input_data["description"])
    return {"error": f"Unknown tool: {name}"}

# The agentic loop
def run_agent(user_request: str) -> str:
    messages = [{"role": "user", "content": user_request}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if b.type == "text")

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  → Calling: {block.name}({block.input})")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

        # Continue the loop with results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


# Example invocation
if __name__ == "__main__":
    result = run_agent(
        "Customer sarah@acmecorp.com emailed saying her order from last week "
        "hasn't arrived. Look her up, check her orders, send her an apology with "
        "a 10% discount code, and create a Jira ticket to investigate with the logistics team."
    )
    print(result)
```

---

## Learning Progression (Recommended Order)

| Stage | Use Case | Systems | What You Learn |
|-------|----------|---------|---------------|
| **1** | Support ticket lookup | Freshdesk + HubSpot | Basic multi-tool routing |
| **2** | Customer email + CRM update | Gmail + HubSpot | Auth flows, write operations |
| **3** | Sprint planner | Notion + Jira | Reading docs, creating structured data |
| **4** | Invoice chaser | Airtable + SendGrid | Scheduled agents, filtering |
| **5** | Full incident response | Slack + Supabase + GitHub + Jira | Multi-system orchestration |


## How to run
az login or z login --tenant <tenant-id> --use-device-code
source .venv/bin/activate
pip install -r requirements-dev.txt

##When new packages are added in requirements.in or requirements-dev.in
pip-compile requirements-dev.in -o requirements-dev.txt