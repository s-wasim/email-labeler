import asyncio
from jose import jwt
from datetime import datetime, timedelta, UTC
from api.utils.credentials_manager import SecretManager, SecretName

class JWTManager:
    def __init__(self, token_expiry_time:int=None):
        jwt_secrets = SecretManager.get_secret(SecretName.JWT_API)
        self.__secret = jwt_secrets['jwt_secret']
        self.__decode_secret = jwt_secrets['jwt_decode_secret']
        self.__algorithm = jwt_secrets['jwt_algorithm']
        self.__jwt_expiry_seconds = token_expiry_time if token_expiry_time else jwt_secrets.get('jwt_expiry_seconds', 3600)
        self.__token = None
        self.token_event = asyncio.Event()

    def create_jwt_token(self, data: dict):
        if not self.__token:
            to_encode = data.copy()
            expire = datetime.now(UTC) + timedelta(seconds=self.__jwt_expiry_seconds)
            to_encode.update({"exp": expire})
            self.token_event.set()
            self.__token = jwt.encode(to_encode, self.__secret, algorithm=self.__algorithm)
    
    @property
    def token(self):
        return self.__token

    def verify_jwt_token(self, token: str):
        assert self.__token is not None, 'Need to define the token to compare against'
        decoded_private = jwt.decode(token, self.__decode_secret, algorithms=[self.__algorithm])
        decoded = jwt.decode(decoded_private['api_token'], self.__secret, algorithms=[self.__algorithm])
        return decoded
