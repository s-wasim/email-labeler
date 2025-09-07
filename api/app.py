import asyncio
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
import requests

from utils import *

class DataManager:
    def __init__(self):
        self.__google_flow = AuthFlowGoogle()
        self.__token_manager_api = JWTManager()

    @property
    def google_flow(self):
        return self.__google_flow
    @property
    def token_manager_api(self):
        return self.__token_manager_api


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
data_store = DataManager()

@app.get("/")
def close_tab():
    return {'command': "You may now close this tab as authentication is complete"}

@app.get("/auth/login")
def login():
    flow = data_store.google_flow.flow
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="false"
    )
    return RedirectResponse(auth_url)

@app.get('/auth/callback')
def callback(code: str):
    flow = data_store.google_flow.flow
    flow.fetch_token(code=code)
    creds = flow.credentials
    data_store.token_manager_api.create_jwt_token({'access_token': creds.token})
    return RedirectResponse('http://localhost:8000/')

@app.get("/token")
async def get_api_token():
    if not data_store.token_manager_api.token:
        try:
            await asyncio.wait_for(
                data_store.token_manager_api.token_event.wait(),
                timeout=300
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Token not available yet")

    return {"api_token": data_store.token_manager_api.token}

@app.get("/labels")
def get_labels(token: str = Depends(oauth2_scheme)):
    try:
        payload = data_store.token_manager_api.verify_jwt_token(token)
        google_token = payload.get('access_token')
        headers = {"Authorization": f"Bearer {google_token}"}

        resp = requests.get(
            'https://gmail.googleapis.com/gmail/v1/users/me/labels',
            headers=headers
        )
        resp.raise_for_status()
        labels = resp.json().get('labels')
        return { 
            'labels_user': [
                {'id': label['id'], 'name': label['name']} 
                for label in labels 
                if label.get('type') and label['type'] == 'user'
            ],
            'labels_system': [
                {'id': label['id'], 'name': label['name']}
                for label in labels 
                if label.get('type') and label['type'] == 'system'
            ]
        }
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gmail API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
    
@app.post("/labels")
def create_label(new_label_name: str, token: str = Depends(oauth2_scheme)):
    try:
        payload = data_store.token_manager_api.verify_jwt_token(token)
        google_token = payload.get("access_token")
        headers = {
            "Authorization": f"Bearer {google_token}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/labels",
            headers=headers,
            json={
                "name": new_label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show"
            }
        )
        response.raise_for_status()
        label_info = response.json()
        return {
            "labelId": label_info.get("id"),
            "name": label_info.get("name")
        }
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gmail API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/emails")
def get_emails(PageToken:str = 'false', token: str = Depends(oauth2_scheme)):
    chunk_size = 10
    try:
        # Decode API token to get Google OAuth access token
        payload = data_store.token_manager_api.verify_jwt_token(token)
        google_token = payload.get("access_token")
        headers = {"Authorization": f"Bearer {google_token}"}

        parameters = {
            "includeSpamTrash": False, 
            "maxResults": chunk_size,
        }
        if PageToken != 'false':
            parameters['nextPageToken'] = PageToken
        resp = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params=parameters
        )
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        next_page_token = resp.json().get("nextPageToken", None)

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

            snipet = detail.get("snipet", "")
            payload = detail.get("payload", {})
            headers_list = payload.get("headers", [])

            subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "No Subject")
            from_ = next((h["value"] for h in headers_list if h["name"] == "From"), "Unknown Sender")
            date_ = next((h["value"] for h in headers_list if h["name"] == "Date"), "Unknown Date")

            labels = detail.get("labelIds", [])

            # Attachments metadata
            attachments = []
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("filename"):
                        attachments.append({
                            "filename": part["filename"],
                            "mimeType": part.get("mimeType"),
                            "size": part.get("body", {}).get("size")
                        })

            results.append({
                "id": msg_id,
                "subject": subject,
                "from": from_,
                "date": date_,
                "labels": labels,
                "snipet": snipet,
                "attachments": attachments
            })

        return {"emails": results, "nextPageToken": next_page_token}
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gmail API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
    

@app.post("/emails/{msg_id}/label")
def assign_label(msg_id: str, label_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Decode API token to get Google OAuth access token
        payload = data_store.token_manager_api.verify_jwt_token(token)
        google_token = payload.get("access_token")
        headers = {"Authorization": f"Bearer {google_token}"}

        # Step 1: Call Gmail API to modify message
        body = {
            "addLabelIds": [label_id]
        }

        resp = requests.post(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify",
            headers=headers,
            json=body
        )
        resp.raise_for_status()

        return resp.json()
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gmail API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
