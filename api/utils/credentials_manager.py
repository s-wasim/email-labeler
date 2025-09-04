from enum import Enum
from settings import secrets

class SecretName(Enum):
    GOOGLE = 'google_secrets'
    JWT_API = 'jwt_secrets_api'

class SecretManager:
    @staticmethod
    def get_secret(secret: SecretName):
        return secrets[secret.value]

