from google_auth_oauthlib.flow import Flow
from .credentials_manager import SecretManager, SecretName

class AuthFlowGoogle:
    def __init__(self):
        """
            args define the additional scopes allowed within the authentication process
        """
        google_secrets = SecretManager.get_secret(SecretName.GOOGLE)
        self.__redirect_uri = google_secrets['client_redirect_uri']
        self.__flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': google_secrets['client_id'],
                    'client_secret': google_secrets['client_secret'],
                    'auth_uri': "https://accounts.google.com/o/oauth2/auth",
                    'token_uri': "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/gmail.modify"
            ],
            redirect_uri=google_secrets['client_redirect_uri'],
        )

    @property
    def flow(self):
        return self.__flow
    @property
    def redirect_uri(self):
        return self.__redirect_uri
    
if __name__ == '__main__':
    google_auth = AuthFlowGoogle()
    google_auth.flow