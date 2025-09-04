import webbrowser

import requests
import streamlit as st

from utils import encode_tok

# Your FastAPI server
API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Gmail Fetcher", layout="centered")

st.title("📧 Gmail Fetcher via FastAPI + Streamlit")
st.markdown("A demo to login with Google and fetch emails.")

# --- State: keep token
if "api_token" not in st.session_state:
    st.session_state.api_token = None

# --- 1. LOGIN BUTTON ---
st.subheader("Step 1: Login with Google")
if st.button("🔑 Login with Google", use_container_width=True):
    # open /auth/login in a new browser tab
    webbrowser.open_new_tab(f"{API_BASE}/auth/login")
    st.info("A new tab has been opened for Google login. Complete the flow and come back here.")
    st.session_state.api_token = encode_tok(requests.get('http://localhost:8000/token').json())

# --- 2. Enter API Token ---
st.subheader("Step 2: API Token Status")

if st.session_state.api_token:
    st.success("✅ API Token loaded")

# --- 3. FETCH EMAILS ---
st.subheader("Step 3: Fetch Emails")

if st.button("📩 Fetch Emails", use_container_width=True):
    if not st.session_state.api_token:
        st.error("You need to provide an API token first.")
    else:
        try:
            headers = {"Authorization": f"Bearer {st.session_state.api_token}"}
            r = requests.get(f"{API_BASE}/emails", headers=headers)
            if r.status_code == 200:
                data = r.json()

                # Gmail returns list of message metadata, you may need to fetch each message
                messages = data.get("emails", [])
                if not messages:
                    st.warning("No emails found.")
                else:
                    for msg in messages:  # limit to first 5 for demo
                        msg_id = msg["id"]
                        subject = msg["subject"]
                        labels = msg["labels"]
                        # mimeType, size
                        attachements = '\n'.join([
                            f"File Name: {attachment['filename']} - Mime Type: {attachment['mimeType']} - Size: {attachment['size']}"
                            for attachment in msg["attachments"]
                        ]) if len(msg['attachments']) > 0 else "No attachments"
                        st.write("### ✉️", subject)
                        st.write("**Labels:**", ", ".join(labels))
                        st.text_area("Attachements", attachements, height=150, key=f"attachments_{msg_id}")
                        st.divider()
            else:
                st.error(f"Error fetching emails: {r.status_code} - {r.text}")
        except Exception as e:
            st.error(f"Exception: {e}")
