import json
from fastapi import APIRouter,status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi_sqlalchemy import db
from fastapi_socketio import SocketManager
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

socket_manager = ConnectionManager()

# @router.sio.on('join')
# async def handle_join(sid, *args, **kwargs):
#     await router.sio.emit('lobby', 'User joined')

# fastapi websocket which is use for the send messages to eachother via socket 
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await socket_manager.connect(websocket) # connecteion eshtablish 
    try:
        while True:
            data = await websocket.receive_text() # receive message 
            await socket_manager.send_personal_message(f"You wrote: {data}", websocket)
            message = {"clientId":client_id,"message":data}
            await socket_manager.broadcast(json.dumps(message)) # send message to each other
            
    except WebSocketDisconnect:
        socket_manager.disconnect(websocket) # disconnect with server
        message = {"clientId":client_id,"message":"Offline"}
        await socket_manager.broadcast(json.dumps(message))