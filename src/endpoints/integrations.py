from fastapi import APIRouter
from typing import List,Dict
from datetime import datetime
from fastapi_sqlalchemy import db
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..dependencies.env import SENDGRID_API_KEY,SENDGRID_EMAIL
from ..schemas.integrationSchema import SlackSchema,EmailSchema,SendgridMailSchema
from ..models.integrations import Slack,SendEmail
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/api/integrations/v1",
    tags=["Integrations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/slack")
async def slack_integration(data:SlackSchema):
    """
    Slack channel integration by user
    """
    try:
        new_channel = Slack(channel_name=data.data['incoming_webhook']['channel'],channel_id=data.data['incoming_webhook']['channel_id'],workspace_name=data.data['team']['name'],bot_token=data.data['access_token'],user_id=data.userId)
        db.session.add(new_channel)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "Connected Successfully!"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't connect with Slack"})

@router.get('/get_slack')
async def get_connected_channels(userId:int):
    """
    Get all connected channels by user
    """
    try:
        all_channels = db.session.query(Slack).filter_by(user_id = userId).all()
        channels = []
        for ch in all_channels:
            get_channel = {"id":ch.id,"channel":(ch.workspace_name+' - '+ch.channel_name)}
            channels.append(get_channel)
        return JSONResponse(status_code = 200, content = {"channels":channels})
    except Exception as e:
        print(e, "at get slack channels. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"There is no channels available!"})

@router.post("/sendgrid_email")
async def add_sendgrid_email(data:SendgridMailSchema):
    """
    Set Sendgrid account by user
    """
    try:
        sg_email = SendEmail(from_email=data.from_email,secret=data.secret,user_id=data.userId)
        db.session.add(sg_email)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "Added Successfully!"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":""})

@router.get('/get_email')
async def get_sendgid_email(userId:int):
    """
    Get all emails set by user
    """
    try:
        all_emails = db.session.query(SendEmail).filter_by(user_id = userId).all()
        emails = []
        for e in all_emails:
            get_email = {"id":e.id,"email":e.from_email}
            emails.append(get_email)
        return JSONResponse(status_code = 200, content = {"emails":emails})
    except Exception as e:
        print(e, "at geting emails. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"Can't get the emails!"})

@router.post("/send_email")
async def slack_integration(user:EmailSchema):
    """
    Send Email by user to customers
    """
    try:
        if not user.customEmail:
            message = Mail(
            from_email=SENDGRID_EMAIL,
            to_emails=user.to_email,
            subject=user.subject,
            html_content='<p>'+user.text+'</p>')
            try:
                send_mail= SendGridAPIClient(SENDGRID_API_KEY)
                send_mail.send(message)
            except Exception as e:
                print(e,"at sending email. Time:", datetime.now())
                return JSONResponse(status_code=404, content={"errorMessage":"Can't send email"})
        else:
            message = Mail(
            from_email=SENDGRID_EMAIL,
            to_emails=user.to_email,
            subject=user.subject,
            html_content='<p>'+user.text+'</p>')
            try:
                send_mail= SendGridAPIClient(SENDGRID_API_KEY)
                send_mail.send(message)
            except Exception as e:
                print(e,"at sending email. Time:", datetime.now())
                return JSONResponse(status_code=404, content={"errorMessage":"Can't send email"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't connect with Slack"})