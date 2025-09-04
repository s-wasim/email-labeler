import base64
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
import requests

import api.utils as utils

class DataManager:
    def __init__(self):
        self.__google_flow = utils.AuthFlowGoogle()
        self.__google_token = None
        self.__token_manager_api = utils.JWTManager()

    @property
    def google_flow(self):
        return self.__google_flow
    @property
    def token_manager_api(self):
        return self.__token_manager_api


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
data_store = DataManager()

@app.get("/auth/login")
def login():
    flow = data_store.google_flow.flow
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    return RedirectResponse(auth_url)

@app.get('/auth/callback')
def callback(code: str):
    flow = data_store.google_flow.flow
    flow.fetch_token(code=code)
    creds = flow.credentials
    data_store.token_manager_api.create_jwt_token({'access_token': creds.token})
    return {'api_token': data_store.token_manager_api.token}

@app.get("/token")
def get_api_token():
    return {'api_token': data_store.token_manager_api.token}

@app.get("/emails")
def get_emails(token: str = Depends(oauth2_scheme)):
    # Expects encoded token with private key
    try:
        google_token = data_store.token_manager_api.verify_jwt_token(token)
        headers = {
            'Authorization': f"Bearer {google_token['access_token']}"
        }
        response = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=headers)
        response.raise_for_status()
    except HTTPException as e:
        raise e
    except AssertionError as e:
        raise e
    
    return response.json()


@app.get("/fetch_emails")
def get_emails(token: str = Depends(oauth2_scheme)):
    try:
        # Decode API token to get Google OAuth access token
        payload = data_store.token_manager_api.verify_jwt_token(token)
        google_token = payload.get("access_token")

        headers = {"Authorization": f"Bearer {google_token}"}

        # Step 1: Fetch message list
        resp = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"maxResults": 5}  # limit to first 5 emails for demo
        )
        resp.raise_for_status()
        messages = resp.json().get("messages", [])

        results = []

        # Step 2: For each message, fetch full details
        for msg in messages:
            msg_id = msg["id"]
            detail_resp = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers
            )
            detail_resp.raise_for_status()
            detail = detail_resp.json()

            payload = detail.get("payload", {})
            headers_list = payload.get("headers", [])

            subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "No Subject")
            from_ = next((h["value"] for h in headers_list if h["name"] == "From"), "Unknown Sender")
            date_ = next((h["value"] for h in headers_list if h["name"] == "Date"), "Unknown Date")

            labels = detail.get("labelIds", [])

            # Extract plain-text body if available
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain" and "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break
            elif "data" in payload.get("body", {}):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

            # Attachments metadata
            attachments = []
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("filename"):
                        attachments.append({
                            "filename": part["filename"],
                            "mimeType": part.get("mimeType"),
                            "size": part.get("body", {}).get("size"),
                            "attachmentId": part.get("body", {}).get("attachmentId")
                        })

            results.append({
                "id": msg_id,
                "subject": subject,
                "from": from_,
                "date": date_,
                "labels": labels,
                "snippet": detail.get("snippet", ""),
                "body": body,
                "attachments": attachments
            })

        return {"emails": results}

    except Exception as e:
        raise e