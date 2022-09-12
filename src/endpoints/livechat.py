from email import message
from fastapi import APIRouter, Depends , encoders, UploadFile,status
from fastapi.responses import JSONResponse, Response
from fastapi_sqlalchemy import db
from datetime import datetime
from typing import List,Dict

from ..schemas.livechatSchema import *
from ..models.livechat import *

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/livechat",
    tags=["Live Chat"],
    responses={404: {"description": "Not found"}},
)

@router.post("/connect")
async def connection_establish():
    return JSONResponse(status_code=status.HTTP_200_OK,message={"Success"})