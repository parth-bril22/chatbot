import bcrypt
import re
from fastapi import APIRouter
from uuid import uuid4
from fastapi import Depends, HTTPException
from fastapi_sqlalchemy import db
from datetime import datetime
from fastapi.responses import JSONResponse

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..models.users import User as ModelUser
from ..models.users import Password_tokens
from ..schemas.userSchema import User as SchemaUser
from ..schemas.userSchema import LoginSchema as lg
from ..schemas.userSchema import PasswordResetSchema, PasswordChangeSchema

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/users/v1",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)

def validate_user(user:ModelUser):
    """
    Validate if email id already exists, is valid and passowrd. Takes ModelUser as input
    """
    
    if(bool(db.session.query(ModelUser).filter_by(email = user.email).first())):
        return JSONResponse(status_code=404, content = {"errorMessage" : 'Email already exists'})

    elif not (re.fullmatch( r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user.email)):
        return JSONResponse(status_code=404, content = {"errorMessage" : 'Enter valid email'})

    elif (len(user.password) < 7):
        return JSONResponse(status_code=404, content = {"errorMessage" : 'Password must be greater than 6 characters'})

    elif not (re.fullmatch(r'[a-zA-Z]+$', user.first_name) and re.fullmatch(r'[A-Za-z]+$', user.last_name)):
        return JSONResponse(status_code=404, content = {"errorMessage" : 'Enter valid name'})

    else:
        return True

@router.post("/signup/" )
async def signup(user: SchemaUser):
    try:
        validated_user = validate_user(user)
        if (validated_user != True): 
            return validated_user
        else:
            hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
            token = auth_handler.encode_token(user.email)
            db_user = ModelUser(email = user.email, password = hashed_password.decode('utf-8'), first_name = user.first_name, last_name = user.last_name, created_at = datetime.today().isoformat(),token = token)
            db.session.add(db_user)
            db.session.commit()
            user_id = db.session.query(ModelUser.id).filter_by(id=db_user.id).first()
            return JSONResponse(status_code=200, content = {'message': "Signup Successful",'token':token, "refresh_token" : auth_handler.create_refresh_token(user.email),'user_id':user_id[0]})
    except Exception as e:
        print("Error at signup: ", e)
        return JSONResponse(status_code=404, content={"errorMessage": "Please check inputs!"})
        
async def get_user_by_email(my_email: str):
    """
    Checks if the email exists in the DB. If not, returns false. If it does, returns all details of the user in User Model form from models.py.
    """
    user = db.session.query(ModelUser).filter_by(email=my_email).first()
    if(user == None):
        return False
    return ModelUser(id = user.id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at=user.created_at)

@router.post("/login/")
async def authenticate_user(input_user: lg):
    try:
        user = await get_user_by_email(input_user.email)
        if (not user) or (not bcrypt.checkpw(input_user.password.encode('utf-8'), user.password.encode('utf-8'))):
            return JSONResponse(status_code=401, content = {"errorMessage" : 'Invalid username or password'})
        else:   
            token = auth_handler.encode_token(input_user.email)
            user_id = db.session.query(ModelUser.id).filter_by(email=input_user.email).first()
            return JSONResponse(status_code=200, content={"message" : "success", 'token':token, "refresh_token" : auth_handler.create_refresh_token(input_user.email),'user_id':user_id[0]})#valid for 1 minute and 30 seconds, change expiration time in auth.py
    except Exception as e:
        print("Error at login: ", e)
        return JSONResponse(status_code=404, content={"errorMessage": "Please check inputs!"})
    """
    The auth.py file has the function auth_wrapper which validates the token by decoding it and checking the credentials.
    Using that function , the details can only be accessed if there is valid JWT token in the header
    This function is only to demonstrate that. To run this:
    curl --header "Authorizaion: Bearer entertokenhere" localhost:8000/protected
    """

@router.post('/refresh')
async def refresh( refresh_token : str):
    try:
        payload = auth_handler.decode_refresh_token(refresh_token)
            # Check if token is not expired
        if datetime.utcfromtimestamp(payload.get('exp')) > datetime.utcnow():
            email = payload.get('email')
            # Validate email
            user = await get_user_by_email(email)
            if user:
                # Create and return token
                return JSONResponse(status_code=200, content={"message" : "success", 'access_token': auth_handler.encode_token(email)})

    except Exception:
        return JSONResponse(status_code=401, content = {"errorMessage" : 'Unauthorized'})
    return JSONResponse(status_code=401, content = {"errorMessage" : 'Unauthorized'})


def send_mail(my_uuid:str):
    """
    send password reset email to user via sendgrid.
    """
    message = Mail(
    from_email='testforfastapi@gmail.com',
    to_emails='testforfastapi@gmail.com',
    subject='Password Reset',
    html_content = 'Hello! <p> Your UUID is:<p> https://chatbot-apis-dev.herokuapp.com/reset_password_link?my_uuid=' + str(my_uuid) +"<p> The link will expire in 10 minutes.")
    link1 = ("https://chatbot-apis-dev.herokuapp.com/reset_password_link?my_uuid=" + str(my_uuid))
    try:
        sg = SendGridAPIClient('SENDGRID_API_CLIENT')
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
        return {'message': 'Link sent, please check mail', "link" : link1}
    except Exception:
        return JSONResponse(status_code=404,content = {"message" : 'Sorry!We could not send the link right now'})


@router.post('/request_change_password')
async def req_change_password(email_id : str):
    my_email =  email_id
    user = db.session.query(ModelUser).filter_by(email = my_email).first()

    if(user == None):
        return JSONResponse(status_code=404,content = {"message" : 'The user is not registered'})

    my_id = user.id
    my_uuid = uuid4()

    db_user = Password_tokens(id = my_id, uuid = str(my_uuid), time = datetime.today().isoformat(), used = False)
    db.session.merge(db_user)
    db.session.commit()
    return send_mail(my_uuid)    

def get_uuid_details(my_uuid:str):
    """
    get id and time generated of the entered uuid
    """
    try:
        user = db.session.query(Password_tokens).filter_by(uuid = str(my_uuid)).first()
    except:
        return JSONResponse(status_code=401, content = {"message" : 'UUID entered incorrectly'})

    if(user == None):
        return JSONResponse(status_code=401, content = {"message" : 'UUID not found'})

    return Password_tokens(id = user.id, uuid = my_uuid, time = user.time, used = user.used)


async def get_user_by_id(my_id: int):
    """
   Get the user info with id 
    """
    user = db.session.query(ModelUser).filter_by(id = my_id).first()
    if(user == None):
        return False
    return ModelUser(id = my_id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at = user.created_at)

@router.post('/reset_password_link')
async def reset_password_link(my_uuid:str,ps:PasswordResetSchema):
    uuid_details = get_uuid_details((my_uuid))

    if(uuid_details.used == True):
        return JSONResponse(status_code=401,content = {"message" : 'Link already used once'})

    mins_passed = ((datetime.today().isoformat() - uuid_details.time).seconds)/60
    if(mins_passed > 10):
        return JSONResponse(status_code=401, content = {"message" : 'More than 10 minutes have passed'})
    else:
        new_user = await get_user_by_id(uuid_details.id)
        if(ps.password == ps.confirm_password): 
            if(len(ps.password) < 7):
                raise HTTPException(status_code=401, detail = 'Passwords length < 7')
            else:
                new_user.password =  bcrypt.hashpw(ps.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.session.query(ModelUser).filter_by(id = new_user.id).update(dict(password = new_user.password))
                db.session.query(Password_tokens).filter_by(id = uuid_details.id).update(dict(used = True))
                db.session.commit()
                db.session.close()
                return JSONResponse(status_code=200, content={'message': "success"})   
        else:
            return JSONResponse(status_code=400, content = {"message" : 'Passwords are not same'})
    
@router.patch('/change_password')
async def change_password(ps:PasswordChangeSchema, my_email = Depends(auth_handler.auth_wrapper) ):
    user = await get_user_by_email(my_email)
    actual_password = user.password.encode('utf-8')

    if(bcrypt.checkpw(ps.current_password.encode('utf-8'), actual_password)):
        if(ps.new_password == ps.confirm_password and len(ps.new_password) > 6 and ps.new_password != ps.current_password):
            user.password =  bcrypt.hashpw(ps.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.session.merge(user)
            db.session.commit()
            db.session.close()
            return JSONResponse(status_code=200, content={'message':'success'})    
        else:
            return JSONResponse(status_code=400, content = {"message" : 'Passwords must be same and of length greater than 6 and must not be the same as old password '})
    else:
        return JSONResponse(status_code=401, content = {"message" : 'Please enter correct current password'})

@router.delete('/delete_user')
async def delete_user(my_email = Depends(auth_handler.auth_wrapper)):
     db.session.query(ModelUser).filter_by(email = my_email).delete()
     db.session.commit()
     db.session.close()
     return JSONResponse(status_code = 200, content = {'message': 'deleted'})
