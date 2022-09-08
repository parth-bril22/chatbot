import bcrypt
import re
from typing import Dict
from fastapi import APIRouter
from uuid import uuid4
from fastapi import Depends, HTTPException,status
from fastapi_sqlalchemy import db
from datetime import datetime
from fastapi.responses import JSONResponse

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..models.customfields import Variable
from ..models.users import User as ModelUser
from ..models.users import Password_tokens
from ..schemas.userSchema import User as SchemaUser
from ..schemas.userSchema import LoginSchema as lg
from ..schemas.userSchema import PasswordResetSchema, PasswordChangeSchema

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/api/users/v1",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)
def validate_user(user:ModelUser):
    """Validate if email id already exists, is valid and passowrd. Takes ModelUser as input"""
    
    if(bool(db.session.query(ModelUser).filter_by(email = user.email).first())):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content = {"errorMessage" : 'Email already exists'})

    elif not (re.fullmatch( r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user.email)):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content = {"errorMessage" : 'Enter valid email'})

    elif (len(user.password) < 7):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,content = {"errorMessage" : 'Password must be greater than 6 characters'})

    elif not (re.fullmatch(r'[a-zA-Z]+$', user.first_name) and re.fullmatch(r'[A-Za-z]+$', user.last_name)):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content = {"errorMessage" : 'Enter valid name'})

    else:
        return True

async def create_global_variable(schema:Dict):
    """Create a custom global variable"""

    try:
        types = ['String','Number','Boolean','Date','Array']
        
        if schema['type'] in types:

            # check not same name variable
            var_names = [i[0] for i in db.session.query(Variable.name).filter_by(user_id=schema['userId']).all()]
            if schema['name'] in var_names:
                return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,content={"errorMessage":"The variable name "  +{schema['name']}+ "is not allowed"})
            # create the variable
            var = Variable(name = schema['name'],type = schema['type'],user_id=schema['userId'],value=schema['value'])
            db.session.add(var)
            db.session.commit()
            db.session.close()

            return JSONResponse(status_code=status.HTTP_201_CREATED,content={"message":"Created successfully"})
        else:
            return JSONResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE,content={"errorMessage":"Type is not correct"})
    except Exception as e:
        print(e,"at create global variables. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"errorMessage":"Can't create a variable"})

@router.post("/signup/" )
async def signup(user: SchemaUser):
    """User signup"""

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

            # defualt vars
            var_list = [{"name": "id","type": "String","userId": user_id,"value":user_id},{"name": "name","type": "String","userId":user_id,"value":user.first_name },
            {"name": "email","type": "String","userId": user_id,"value":user.email},{"name": "date","type": "String","userId": user_id,"value":datetime.today().isoformat()}]

            for var in var_list:
                await create_global_variable(var)

            return JSONResponse(status_code=status.HTTP_201_CREATED, content = {'message': "Signup Successful",'token':token, "refresh_token" : auth_handler.create_refresh_token(user.email),'user_id':user_id})
    except Exception as e:
        print("Error at signup: ", e)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage": "Please check inputs!"})
        
async def get_user_by_email(my_email: str):
    """Checks if the email exists or not"""

    try:
        user = db.session.query(ModelUser).filter_by(email=my_email).first()
        if(user == None):
            return False
        return ModelUser(id = user.id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at=user.created_at)
    except:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'Please check email'})

@router.post("/login/")
async def authenticate_user(input_user: lg):
    """User login/Signin"""

    try:
        user = await get_user_by_email(input_user.email)
        if (not user) or (not bcrypt.checkpw(input_user.password.encode('utf-8'), user.password.encode('utf-8'))):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"errorMessage" : 'Invalid username or password'})
        else:   
            token = auth_handler.encode_token(input_user.email)
            user_id = db.session.query(ModelUser.id).filter_by(email=input_user.email).first()
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message" : "success", 'token':token, "refresh_token" : auth_handler.create_refresh_token(input_user.email),'user_id':user_id[0]})#valid for 1 minute and 30 seconds, change expiration time in auth.py
    except Exception as e:
        print("Error at login: ", e)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage": "Please check inputs!"})


@router.post('/refresh')
async def refresh( refresh_token : str):
    """For check using refresh token after session is expired"""

    try:
        payload = auth_handler.decode_refresh_token(refresh_token)
            # Check if token is not expired
        if datetime.utcfromtimestamp(payload.get('exp')) > datetime.utcnow():
            email = payload.get('email')
            # Validate email
            user = await get_user_by_email(email)
            if user:
                # Create and return token
                return JSONResponse(status_code=status.HTTP_200_OK, content={"message" : "success", 'access_token': auth_handler.encode_token(email)})

    except Exception:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"errorMessage" : 'Unauthorized'})
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"errorMessage" : 'Unauthorized'})


def send_mail(my_uuid:str):
    """Send password reset link on email of user"""

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
        return {'message': 'Link sent to on your mail,please check', "link" : link1}
    except Exception:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,content = {"message" : 'Sorry!We could not send the link right now'})


@router.post('/request_change_password')
async def req_change_password(email_id : str):
    """Request to change the password by user"""

    try:
        my_email =  email_id
        user = db.session.query(ModelUser).filter_by(email = my_email).first()

        if(user == None):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,content = {"message" : 'The user is not registered'})

        my_id = user.id
        my_uuid = uuid4()

        db_user = Password_tokens(id = my_id, uuid = str(my_uuid), time = datetime.today().isoformat(), used = False)
        db.session.merge(db_user)
        db.session.commit()
        return send_mail(my_uuid)    
    except:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'UUID entered incorrectly'})
    

def get_uuid_details(my_uuid:str):
    """Get id and time generated of the entered uuid"""

    try:
        user = db.session.query(Password_tokens).filter_by(uuid = str(my_uuid)).first()
        if(user == None):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'UUID not found'})

        return Password_tokens(id = user.id, uuid = my_uuid, time = user.time, used = user.used)
    except:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'UUID entered incorrectly'})


async def get_user_by_id(my_id: int):
    """Get the user info by id"""

    try:
        user = db.session.query(ModelUser).filter_by(id = my_id).first()
        if(user == None):
            return False
        return ModelUser(id = my_id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at = user.created_at)
    except Exception as e:
        print(e, "at getting user by id. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"Email is not exists"})
        
@router.post('/reset_password_link')
async def reset_password_link(my_uuid:str,ps:PasswordResetSchema):
    """Reset the password using link which send to registered mail-id"""

    try :
        uuid_details = get_uuid_details((my_uuid))

        if(uuid_details.used == True):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED,content = {"message" : 'Link already used once'})

        mins_passed = ((datetime.today().isoformat() - uuid_details.time).seconds)/60
        if(mins_passed > 10):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'More than 10 minutes have passed'})
        else:
            new_user = await get_user_by_id(uuid_details.id)
            if(ps.password == ps.confirm_password): 
                if(len(ps.password) < 7):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = 'Passwords length < 7')
                else:
                    new_user.password =  bcrypt.hashpw(ps.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db.session.query(ModelUser).filter_by(id = new_user.id).update(dict(password = new_user.password))
                    db.session.query(Password_tokens).filter_by(id = uuid_details.id).update(dict(used = True))
                    db.session.commit()
                    db.session.close()
                    return JSONResponse(status_code=status.HTTP_200_OK, content={'message': "success"})   
            else:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content = {"message" : 'Passwords are not same'})
    except Exception as e:
        print(e, "at reset password. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage":"Sorry,Link expired"})
 
@router.patch('/change_password')
async def change_password(ps:PasswordChangeSchema, my_email = Depends(auth_handler.auth_wrapper)):
    """Change password by user"""

    try:

        user = await get_user_by_email(my_email)
        actual_password = user.password.encode('utf-8')

        if(bcrypt.checkpw(ps.current_password.encode('utf-8'), actual_password)):
            if(ps.new_password == ps.confirm_password and len(ps.new_password) > 6 and ps.new_password != ps.current_password):
                user.password =  bcrypt.hashpw(ps.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.session.merge(user)
                db.session.commit()
                db.session.close()
                return JSONResponse(status_code=status.HTTP_200_OK, content={'message':'success'})    
            else:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content = {"message" : 'Passwords must be same and of length greater than 6 and must not be the same as old password '})
        else:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content = {"message" : 'Please enter correct current password'})
    except Exception as e:
        print(e, "at changing password. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage":"Can't change password"})


@router.delete('/delete_account')
async def delete_user(my_email = Depends(auth_handler.auth_wrapper)):
    """Delete user's account permanently"""

    try:
        db.session.query(ModelUser).filter_by(email = my_email).delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = status.HTTP_200_OK, content = {'message': 'deleted'})
    except Exception as e:
        print(e, "at delete account. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage":"Can't delete account"})

@router.get('/user_profile')
async def user_profile(user_id : int):
    """Get the user profile"""

    try:
        token = db.session.query(ModelUser.token).filter_by(id=user_id).first()[0]
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = status.HTTP_200_OK, content = {'Token': token})
    except Exception as e:
        print(e, "at user proflie. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"errorMessage":"Can't find user"})