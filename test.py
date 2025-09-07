import sys
from email_agent import Agent
from utils import encode_tok, GmailClient

API_BASE = "http://localhost:8000"
MAX_PAGES = 1


def main():
    print("📧 Gmail Fetcher via FastAPI (Terminal Version)")

    # --- Step 1: Get API Token ---
    print("Fetching API token...")
    token_json = GmailClient.get_token(API_BASE)
    if not token_json.get("api_token"):
        print("❌ No API token found. Please login first via the FastAPI backend.")
        sys.exit(1)

    api_token = encode_tok(token_json)
    client = GmailClient(API_BASE, api_token)
    labeler = Agent()
    print("✅ API Token loaded")

    # --- Step 2: Fetch and Label Emails ---
    print("Fetching emails...")
    messages = client.get_emails(MAX_PAGES)
    if not messages:
        print("⚠️ No emails found.")
        return

    label_dict = client.get_labels()

    for msg in messages:
        # Skip if email already has matching label
        if any(lbl in label_dict.values() for lbl in msg["labels"]):
            continue

        # Generate label
        lbl = labeler.generate_label(msg, label_dict.keys())
        label_id = label_dict.get(lbl)

        if label_id:
            client.apply_label(msg["id"], label_id)
            print(f"Applied existing label: {lbl}")
        else:
            new_label_id = client.create_label(lbl)
            label_dict[lbl] = new_label_id
            client.apply_label(msg["id"], new_label_id)
            print(f"Created and applied new label: {lbl}")

    print("✅ All emails labeled successfully")


if __name__ == "__main__":
    main()
