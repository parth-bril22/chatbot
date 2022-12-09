import bcrypt
import boto3
import logging
from re import fullmatch
from typing import Dict
from fastapi import APIRouter, encoders, UploadFile
from uuid import uuid4
from fastapi import Depends, HTTPException, status
from fastapi_sqlalchemy import db
from datetime import datetime
from fastapi.responses import JSONResponse

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..models.customfields import Variable
from ..models.flow import Chat, Flow
from ..models.users import UserInfo as ModelUser
from ..models.users import Password_tokens
from ..schemas.userSchema import User as SchemaUser
from ..schemas.userSchema import LoginSchema
from ..schemas.userSchema import PasswordResetSchema, ChangePasswordSchema

from ..dependencies.auth import AuthHandler
from ..dependencies.config import AWS_ACCESS_KEY, AWS_ACCESS_SECRET_KEY, BUCKET_NAME

auth_handler = AuthHandler()

logger = logging.getLogger(__file__)

router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)



def validate_user_detials(user: ModelUser):
    """Validate the user by email. Takes ModelUser as input"""

    if bool(db.session.query(ModelUser).filter_by(email=user.email).first()):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Email already exists"},
        )

    elif not (
        fullmatch(r"[a-zA-Z]+$", user.first_name)
        and fullmatch(r"[A-Za-z]+$", user.last_name)
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Enter valid name"},
        )

    else:
        return True


async def create_global_variable(schema: Dict):
    """Create a custom global variable"""

    try:
        var_types = ["String", "Number", "Boolean", "Date", "Array"]

        if schema["type"] not in var_types:
            return JSONResponse(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                content={"errorMessage": "Type is not correct"},
            )

        var_names = [
            i[0]
            for i in db.session.query(Variable.name)
            .filter_by(user_id=schema["userId"])
            .all()
        ]
        if schema["name"] in var_names:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "errorMessage": "The variable name "
                    + {schema["name"]}
                    + "is not allowed"
                },
            )

        var = Variable(
            name=schema["name"],
            type=schema["type"],
            user_id=schema["userId"],
            value=schema["value"],
        )
        db.session.add(var)
        db.session.commit()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Created successfully"},
        )
    except Exception as e:
        logger.error(f"Failed to create variables. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't create a variable"},
        )


async def validate_user_email(user_email: str):
    """Checks if the email exists or not"""

    try:
        user = db.session.query(ModelUser).filter_by(email=user_email).first()
        if user is None:
            return False
        return ModelUser(
            id=user.id,
            email=user.email,
            password=user.password,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to checking mail. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Please check email"},
        )


def send_mail(my_uuid: str):
    """Send email to user"""

    message = Mail(
        from_email="testforfastapi@gmail.com",
        to_emails="testforfastapi@gmail.com",
        subject="Password Reset",
        html_content="Hello! <p> UUID :"
        + "<p> https://chatbot-apis-dev.herokuapp.com/reset_password_link?my_uuid="
        + str(my_uuid)
        + "<p> The link will expire in 10 minutes.",
    )
    link1 = "https://chatbot-apis-dev.herokuapp.com/reset_password_link?my_uuid=" + str(
        my_uuid
    )
    try:
        sg = SendGridAPIClient("SENDGRID_API_CLIENT")
        response = sg.send(message)
        logging.debug(response.status_code)
        logging.debug(response.body)
        logging.debug(response.headers)
        return {"message": "Link sent to on your mail,please check", "link": link1}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Sorry!We could not send the link right now"},
        )


def get_uuid_details(my_uuid: str):
    """Get id and time generated of the entered uuid"""

    try:
        user = db.session.query(Password_tokens).filter_by(uuid=str(my_uuid)).first()
        if user is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "UUID not found"},
            )

        return Password_tokens(id=user.id, uuid=my_uuid, time=user.time, used=user.used)

    except Exception as e:
        logger.error(f"Failed to get uuid. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "UUID entered incorrectly"},
        )


async def get_user(userId: int):
    """Get the user info as per id"""

    try:
        user = db.session.query(ModelUser).filter_by(id=userId).first()
        if user is None:
            return False
        return ModelUser(
            id=id,
            email=user.email,
            password=user.password,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to get user. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"Email is not exists"}
        )


@router.post("/signup")
async def signup(user: SchemaUser):
    """User signup"""

    try:
        # user_details_validatation = validate_user_detials(user)
        # if user_details_validatation is not True:
        #     return user_details_validatation
        if bool(db.session.query(ModelUser).filter_by(email=user.email).first()):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Email already exists"},
            )

        elif not (
            fullmatch(r"[a-zA-Z]+$", user.first_name)
            and fullmatch(r"[A-Za-z]+$", user.last_name)
        ):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Enter valid name"},
            )
        else:
            hashed_password = bcrypt.hashpw(
                user.password.encode("utf-8"), bcrypt.gensalt()
            )
            token = auth_handler.encode_token(user.email)
            db_user = ModelUser(
                email=user.email,
                password=hashed_password.decode("utf-8"),
                first_name=user.first_name,
                last_name=user.last_name,
                created_at=datetime.today().isoformat(),
                token=token,
            )
            db.session.add(db_user)
            db.session.commit()

            user_id = db.session.query(ModelUser.id).filter_by(id=db_user.id).first()

            # defualt vars
            var_list = [
                {
                    "name": "id",
                    "type": "String",
                    "userId": user_id[0],
                    "value": user_id[0],
                },
                {
                    "name": "name",
                    "type": "String",
                    "userId": user_id[0],
                    "value": user.first_name,
                },
                {
                    "name": "email",
                    "type": "String",
                    "userId": user_id[0],
                    "value": user.email,
                },
                {
                    "name": "date",
                    "type": "String",
                    "userId": user_id[0],
                    "value": datetime.today().isoformat(),
                },
            ]

            for var in var_list:
                await create_global_variable(var)

            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "message": "Signup Successful",
                    "token": token,
                    "refresh_token": auth_handler.create_refresh_token(user.email),
                    "user_id": user_id[0],
                },
            )
    except Exception as e:
        logger.error(f"Failed to signup. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Please check inputs!"},
        )


@router.post("/login")
def login(input_user: LoginSchema):
    """User login/Signin"""

    try:
        user = db.session.query(ModelUser).filter_by(email=input_user.email).first()
        if (user is None) or (
            not bcrypt.checkpw(
                input_user.password.encode("utf-8"), user.password.encode("utf-8")
            )
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"errorMessage": "Invalid username or password"},
            )
        else:
            token = auth_handler.encode_token(input_user.email)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "success",
                    "token": token,
                    "refresh_token": auth_handler.create_refresh_token(
                        input_user.email
                    ),
                    "user_id": user.id,
                },
            )  # valid for 1 minute and 30 seconds, change expiration time in auth.py
    except Exception as e:
        logger.error(f"Failed to login. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Please check inputs!"},
        )


@router.post("/refresh_token")
async def get_refresh_token(refresh_token: str):
    """For check using refresh token after session is expired"""

    try:
        payload = auth_handler.decode_refresh_token(refresh_token)
        # Check if token is not expired
        if datetime.utcfromtimestamp(payload.get("exp")) > datetime.utcnow():
            email = payload.get("email")
            # Validate email
            user = await validate_user_email(email)
            if user:
                # Create and return token
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "message": "success",
                        "access_token": auth_handler.encode_token(email),
                    },
                )

    except Exception as e:
        logger.error(f"Failed to get refresh_token. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"errorMessage": "Unauthorized"},
        )

@router.post("/request_change_password")
async def change_password_request(email_id: str):
    """Request to change the password by user"""

    try:
        my_email = email_id
        user = db.session.query(ModelUser).filter_by(email=my_email).first()

        if user is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "The user is not registered"},
            )

        my_id = user.id
        my_uuid = uuid4()

        db_user = Password_tokens(
            id=my_id, uuid=str(my_uuid), time=datetime.today().isoformat(), used=False
        )
        db.session.merge(db_user)
        db.session.commit()
        return send_mail(my_uuid)
    except Exception as e:
        logger.error(f"Failed to send mail for change password. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "UUID entered incorrectly"},
        )


@router.post("/reset_password")
async def reset_password(my_uuid: str, ps: PasswordResetSchema):
    """Reset the password using link which send to registered mail-id"""

    try:
        uuid_details = get_uuid_details((my_uuid))

        if uuid_details.used is True:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Link already used once"},
            )

        mins_passed = ((datetime.today().isoformat() - uuid_details.time).seconds) / 60
        if mins_passed > 10:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "More than 10 minutes have passed"},
            )
        else:
            new_user = await get_user(uuid_details.id)
            if ps.password == ps.confirm_password:
                if len(ps.password) < 7:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Passwords length < 7",
                    )
                else:
                    new_user.password = bcrypt.hashpw(
                        ps.password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")
                    db.session.query(ModelUser).filter_by(id=new_user.id).update(
                        dict(password=new_user.password)
                    )
                    db.session.query(Password_tokens).filter_by(
                        id=uuid_details.id
                    ).update(dict(used=True))
                    db.session.commit()
                    db.session.close()
                    return JSONResponse(
                        status_code=status.HTTP_200_OK, content={"message": "success"}
                    )
            else:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Passwords are not same"},
                )
    except Exception as e:
        logger.error(f"Failed to reset password. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Sorry,Link expired"},
        )


@router.patch("/change_password")
async def change_password(
    ps: ChangePasswordSchema, token=Depends(auth_handler.auth_wrapper)
):
    """Change password by user"""

    try:

        user = await validate_user_email(token)
        # actual_password = user.password.encode("utf-8")
        if (
            not bcrypt.checkpw(
                ps.current_password.encode("utf-8"), user.password.encode("utf-8")
            )
        ) and (
            not (
                ps.new_password == ps.confirm_password
                and len(ps.new_password) > 6
                and ps.new_password != ps.current_password
            )
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Password should not be same as previous password"},
            )
        newPassword = bcrypt.hashpw(
            ps.new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        db.session.query(ModelUser).filter_by(email=token).update(
            {"password": newPassword}
        )
        db.session.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "success"}
        )
    except Exception as e:
        logger.error(f"Failed to changing password. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't change password"},
        )


@router.delete("/delete_account")
async def delete_user(my_email=Depends(auth_handler.auth_wrapper)):
    """Delete user's account permanently"""

    try:
        db.session.query(ModelUser).filter_by(email=my_email).delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "deleted"}
        )
    except Exception as e:
        logger.error(f"Failed to delete user. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't delete account"},
        )


@router.get("/user_profile")
async def get_user_profile(user_id: int):
    """Get the user profile"""

    try:
        token = db.session.query(ModelUser.token).filter_by(id=user_id).first()[0]
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"Token": token})
    except Exception as e:
        logger.error(f"Failed to get user profile. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't find user"},
        )


@router.get("/visitors")
async def get_visitors(flow_id: int):
    """Get the visitor information"""

    try:
        visitor_list = db.session.query(Chat).filter_by(flow_id=flow_id).all()

        flow_name = db.session.query(Flow.name).filter_by(id=flow_id).first()

        url = ""
        final_visitor_list = []
        for i in visitor_list:
            final_visitor_list.append(
                {
                    "flow_id": i.flow_id,
                    "name": None,
                    "flow_name": flow_name[0],
                    "Bot": url,
                    "visitor_id": i.visitor_id,
                    "visited_ip": i.visitor_ip,
                    "updated_at": i.updated_at,
                    "visited_at": i.visited_at,
                    "visitor_token": i.visitor_token,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=encoders.jsonable_encoder(final_visitor_list),
        )
    except Exception as e:
        logger.error(f"Failed to get visitors. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't find any visitor"},
        )

@router.post("/avatar")
async def profile_image(user_id: int,file: UploadFile):
    """Upload profile image by user"""

    try:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_ACCESS_SECRET_KEY,
        )
        bucket = s3.Bucket(BUCKET_NAME)

        CONTENT_TYPES = [
            "image/png",
            "image/jpeg",
            "image/jpg",
        ]
        if file.content_type in CONTENT_TYPES:
            bucket.upload_fileobj(
                file.file,
                "profileavatar/" + str(user_id) + "/" + file.filename,
                ExtraArgs={"ContentType": file.content_type},
            )

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com/profileavatar/{user_id}/{file.filename}"

        db.session.query(ModelUser).filter_by(id=user_id).update({"avatar":s3_file_url})
        db.session.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "success"})
    except Exception as e:
        logger.error(f"Failed to upload profile picture. ERROR: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "File not uploaded successfully!"},
        )
