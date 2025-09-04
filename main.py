import webbrowser
import streamlit as st

from email_agent import Agent
from utils import encode_tok, GmailClient

API_BASE = "http://localhost:8000"

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

# --- Step 1: Login ---
st.subheader("Step 1: Login with Google")
if st.button("🔑 Login with Google", use_container_width=True):
    webbrowser.open_new_tab(f"{API_BASE}/auth/login")
    st.info("A new tab has been opened for Google login. Complete the flow and return here.")
    token_json = GmailClient(API_BASE, "").get_token()
    st.session_state.api_token = encode_tok(token_json)
    st.session_state.client = GmailClient(API_BASE, st.session_state.api_token)
    st.session_state.email_labeler = Agent()

# --- Step 2: Token status ---
st.subheader("Step 2: API Token Status")
if st.session_state.api_token:
    st.success("✅ API Token loaded")
else:
    st.warning("No API token found. Please login first.")

# --- Step 3: Fetch + Label ---
st.subheader("Step 3: Label Emails")
if st.button("📩 Fetch Emails", use_container_width=True):
    if not st.session_state.api_token:
        st.error("You need to login first.")
    else:
        try:
            client = st.session_state.client
            labeler = st.session_state.email_labeler

            label_dict = client.get_labels()
            messages = client.get_emails()

            if not messages:
                st.warning("No emails found.")
            else:
                for msg in messages[:5]:  # limit for demo
                    # Skip if email already has matching label
                    if any(lbl in label_dict.values() for lbl in msg["labels"]):
                        continue

                    # Generate label
                    lbl = labeler.generate_label(msg, label_dict.keys())
                    label_id = label_dict.get(lbl)

                    if label_id:
                        client.apply_label(msg["id"], label_id)
                    else:
                        new_label_id = client.create_label(lbl)
                        client.apply_label(msg["id"], new_label_id)

                st.divider()
                st.write("### ✅ All emails labeled successfully")

        except Exception as e:
            st.error(f"Exception: {e}")
