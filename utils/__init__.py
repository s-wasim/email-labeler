from jose import jwt

from settings import secrets

def encode_tok(token):
    return jwt.encode(token, secrets['web_secrets']['jwt_secret'], algorithm='HS256')

import requests

class GmailClient:
    def __init__(self, api_base: str, token: str):
        self.api_base = api_base
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_token(self):
        return requests.get(f"{self.api_base}/token").json()

    def get_labels(self):
        r = requests.get(f"{self.api_base}/labels", headers=self.headers)
        r.raise_for_status()
        labels = r.json().get("labels_user", [])
        return {lbl["name"]: lbl["id"] for lbl in labels}

    def get_emails(self):
        r = requests.get(f"{self.api_base}/emails", headers=self.headers)
        r.raise_for_status()
        return r.json().get("emails", [])

    def apply_label(self, msg_id: str, label_id: str):
        return requests.post(
            f"{self.api_base}/emails/{msg_id}/label",
            headers=self.headers,
            params={"label_id": label_id}
        )

    def create_label(self, name: str):
        r = requests.post(
            f"{self.api_base}/labels",
            headers=self.headers,
            params={"new_label_name": name}
        )
        r.raise_for_status()
        return r.json().get("labelId")
