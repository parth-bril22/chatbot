# import jwt
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta


class AuthHandler():
    security = HTTPBearer()
    secret = 'brIlwORkS'
    def encode_token(self, email_id):
        payload = {
            #token issued at - present time
            'iat': datetime.utcnow(),
            #token expiration time - 2mins 30 seconds
            'exp': datetime.utcnow() + timedelta(days=0, minutes=2 ,seconds= 30),
            #token cannot be used before - present time
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