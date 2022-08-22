from pickletools import int4
from fastapi import APIRouter
from typing import List,Dict
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.integrationSchema import SlackSchema
from ..models.integrations import Slack
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/integrations/v1",
    tags=["Integrations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/slack")
# async def slack_integration(channel:str, message:str,access_token:str):
async def slack_integration(data:SlackSchema):
    """
    Slack channel integration
    """
    try:
        new_channel = Slack(channel_name=data['data']['incoming_webhook']['channel'],channel_id=data['data']['incoming_webhook']['channel_id'],workspace_name=data['data']['team']['name'],bot_token=data['data']['access_token'],user_id=data['userID'])
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
    Get all connected channels 
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
