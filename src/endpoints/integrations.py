from fastapi import APIRouter
from typing import List,Dict
from datetime import datetime
from fastapi_sqlalchemy import db

from ..models.integrations import Slack
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/integrations/v1",
    tags=["Integrations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/slack")
# async def slack_integration(channel:str, message:str,access_token:str):
async def slack_integration(data:Dict):
    """
    Slack channel integration
    """
    try:
        new_channel = Slack(channel_name=data['incoming_webhook']['channel'],channel_id=data['incoming_webhook']['channel_id'],workspace_name=data['team']['name'],bot_token=data['access_token'])
        db.session.add(new_channel)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "Connected Successfully!"})
    except Exception as e:
        print(e,"at slack connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't connect with Slack"})

@router.post('/get_slack')
async def get_connected_channels():
    """
    Get all connected channels 
    """
    try:
        all_channels = db.session.query(Slack).all()
        return JSONResponse(status_code = 200, content = {"channels": all_channels})
    except Exception as e:
        print(e, "at creating workspace. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"Can't create a workspace"})
