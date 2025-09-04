from jose import jwt

from settings import secrets

def encode_tok(token):
    return jwt.encode(token, secrets['web_secrets']['jwt_secret'], algorithm='HS256')