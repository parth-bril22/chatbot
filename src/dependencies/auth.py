import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta


class AuthHandler():
    security = HTTPBearer()
    secret = 'brIlwORkS'
    def encode_token(self, email_id):
        payload = {
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=1),
            'nbf': datetime.utcnow(),
            'email': email_id
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm='HS256'
        )

    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return payload['email']
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Signature has expired')
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail='Invalid token')

    def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return self.decode_token(auth.credentials)
    
    def decode_refresh_token(self, token):
        return jwt.decode(token, self.secret, algorithms=['HS256'])

    def create_access_token(self, email_id, expire_time):
        payload = {
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + expire_time,
            'nbf': datetime.utcnow(),
            'email': email_id
        }
        return jwt.encode(payload,self.secret,algorithm='HS256')

    def create_refresh_token(self, email):
        expires = timedelta(minutes = 60 * 24 * 30)#30 days
        return self.create_access_token(email, expires)