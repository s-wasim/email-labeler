import webbrowser
import streamlit as st

from email_agent import Agent
from utils import encode_tok, GmailClient

API_BASE = "http://localhost:8000"
MAX_PAGES = 1

st.set_page_config(page_title="Gmail Fetcher", layout="centered")
st.title("📧 Gmail Fetcher via FastAPI + Streamlit")
st.markdown("Login with Google, fetch emails, and auto-label them.")

# --- State ---
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "client" not in st.session_state:
    st.session_state.client = None
if "email_labeler" not in st.session_state:
    st.session_state.email_labeler = None
if "log_messages" not in st.session_state:
    st.session_state.log_messages = []


def log_message(msg: str):
    """Append message to logs and refresh display."""
    st.session_state.log_messages.append(msg)


# --- Step 1: Login ---
st.subheader("Step 1: Login with Google")
if st.button("🔑 Login with Google", use_container_width=True):
    webbrowser.open_new_tab(f"{API_BASE}/auth/login")
    st.info("A new tab has been opened for Google login. Complete the flow and return here.")
    token_json = GmailClient.get_token(API_BASE)
    if token_json.get("api_token"):
        st.session_state.api_token = encode_tok(token_json)
        st.session_state.client = GmailClient(API_BASE, st.session_state.api_token)
        st.session_state.email_labeler = Agent()
        st.success("✅ Login successful and API token saved")
    else:
        st.error("❌ Login failed. Please try again.")


# --- Step 2: Token status ---
st.subheader("Step 2: API Token Status")
if st.button("Fetch existing Token", use_container_width=True):
    token_json = GmailClient.get_token(API_BASE)
    if token_json.get("api_token"):
        st.session_state.api_token = encode_tok(token_json)
        st.session_state.client = GmailClient(API_BASE, st.session_state.api_token)
        st.session_state.email_labeler = Agent()
        st.success("✅ API Token loaded successfully")
    else:
        st.warning("⚠️ No API token found. Please login first.")

if st.session_state.api_token:
    st.info("🔒 API Token is active")
else:
    st.warning("No API token loaded. Please login first.")


# --- Step 3: Fetch + Label ---
st.subheader("Step 3: Label Emails")
if st.button("📩 Fetch Emails", use_container_width=True):
    if not st.session_state.api_token:
        st.error("You need to login first.")
    else:
        st.session_state.log_messages = []  # clear old logs
        try:
            client = st.session_state.client
            labeler = st.session_state.email_labeler

            label_dict = client.get_labels()
            messages = client.get_emails(MAX_PAGES)

            if not messages:
                st.warning("No emails found.")
            else:
                for msg in messages:
                    # Skip if email already has a known label
                    if any(lbl in label_dict.values() for lbl in msg.get("labels", [])):
                        log_message(f"SKIPPED: Email {msg['id']} already labeled.")
                        continue

                    # Generate label
                    lbl = labeler.generate_label(msg, label_dict.keys())
                    label_id = label_dict.get(lbl)

                    if label_id:
                        client.apply_label(msg["id"], label_id)
                        log_message(f"EMAIL assigned label: {lbl}")
                    else:
                        new_label_id = client.create_label(lbl)
                        label_dict[lbl] = new_label_id
                        client.apply_label(msg["id"], new_label_id)
                        log_message(f"NEW label created: {lbl} → assigned to email {msg['id']}")

                st.success("✅ All emails processed successfully")

        except Exception as e:
            st.error(f"Exception: {e}")
