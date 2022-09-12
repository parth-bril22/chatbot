from fastapi import APIRouter,status
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.integrationSchema import SlackSchema,SendgridMailSchema
from ..models.integrations import Slack,SendEmail
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/slack")
async def slack_integration(data:SlackSchema):
    """Add channel's name,id and bot_token by user into DB"""

    try:
        new_channel = Slack(channel_name=data.data['incoming_webhook']['channel'],channel_id=data.data['incoming_webhook']['channel_id'],workspace_name=data.data['team']['name'],bot_token=data.data['access_token'],user_id=data.userId)
        db.session.add(new_channel)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Success"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage":"Can't add Slack info"})

@router.get('/get_slack')
async def get_connected_channels(userId:int):
    """Get all connected channels by user"""

    try:
        all_channels = db.session.query(Slack).filter_by(user_id = userId).all()
        channels = []
        for ch in all_channels:
            get_channel = {"id":ch.id,"channel":(ch.workspace_name+' - '+ch.channel_name)}
            channels.append(get_channel)
        return JSONResponse(status_code = status.HTTP_200_OK, content = {"channels":channels})
    except Exception as e:
        print(e, "at get slack channels. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"errorMessage":"Channels not found!"})

@router.post("/sendgrid_email")
async def add_sendgrid_email(data:SendgridMailSchema):
    """Set/Add Sendgrid account by user with API key"""

    try:
        sg_email = SendEmail(from_email=data.from_email,secret=data.secret,user_id=data.userId)
        db.session.add(sg_email)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Successfully added!"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errorMessage":"Can't add sendgrid account"})

@router.get('/get_email')
async def get_sendgid_email(userId:int):
    """Get all emails set by user"""

    try:
        all_emails = db.session.query(SendEmail).filter_by(user_id = userId).all()
        emails = []
        for e in all_emails:
            get_email = {"id":e.id,"email":e.from_email}
            emails.append(get_email)
        return JSONResponse(status_code = status.HTTP_200_OK, content = {"emails":emails})
    except Exception as e:
        print(e, "at geting emails. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"errorMessage":"Can't get the emails!"})