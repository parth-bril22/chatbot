from fastapi import APIRouter, status
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.integrationSchema import Slack, SendgridMail
from ..models.integrations import Slack, SendGrid
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
    responses={404: {"description": "Not found"}},
)


@router.post("/slack")
async def slack_integration(data: Slack):
    """Add channel's name,id and bot_token by user into DB"""

    try:
        new_channel = Slack(
            channel_name=data.data["incoming_webhook"]["channel"],
            channel_id=data.data["incoming_webhook"]["channel_id"],
            workspace_name=data.data["team"]["name"],
            bot_token=data.data["access_token"],
            user_id=data.userId,
        )
        db.session.add(new_channel)
        db.session.commit()
        # db.session.close()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content={"message": "Success"}
        )
    except Exception as e:
        print(e, "at slack connection. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't add Slack info"},
        )


@router.get("/get_slack")
async def get_slack_channels(userId: int):
    """Get all connected slack channels by user"""

    try:
        channels = [{
                "id": ch.id,
                "channel": (ch.workspace_name + " - " + ch.channel_name),
            } for ch in db.session.query(Slack).filter_by(user_id=userId).all()]
    
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"channels": channels}
        )
    except Exception as e:
        print(e, "at get slack channels. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Channels not found!"},
        )


@router.post("/sendgrid_email")
async def sendgrid_integration(data: SendgridMail):
    """Set/Add Sendgrid account by user with API key"""

    try:
        sg_email = SendGrid(
            from_email=data.from_email, secret=data.secret, user_id=data.userId
        )
        db.session.add(sg_email)
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Successfully added!"},
        )
    except Exception as e:
        print(e, "at slack connection. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't add sendgrid account"},
        )


@router.get("/get_email")
async def get_sendgrid_emails(userId: int):
    """Get all emails set by user"""

    try:
        emails = [{"id": e.id, "email": e.from_email} for e in db.session.query(SendGrid).filter_by(user_id=userId).all()]
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"emails": emails})
    except Exception as e:
        print(e, "at geting emails. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't get the emails!"},
        )
