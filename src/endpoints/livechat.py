import json
from fastapi import APIRouter,status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import db
# from fastapi_socketio import SocketManager
from datetime import datetime
from typing import List
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

# async def generate_token():


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int,token:str):
    # print(websocket.client)
    # print(websocket.application_state)
    # print(websocket.base_url)
    # print(websocket.cookies)
    # print(websocket.client)
    # print(websocket.get)
    # print(websocket.app)
    # print(websocket.client_state)
    # print(websocket.headers)
    # print(websocket.keys)
    # print(websocket.scope)
    # print(websocket.url)
    print(websocket.values)
    if token != "secret":
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"message": "Please provide right token"})
    await socket_manager.connect(websocket) # connecteion eshtablish 
    try:
        while True:
            data = await websocket.receive_text() # receive message 
            await socket_manager.send_personal_message(f"You wrote: {data}", websocket)# send to private message 
            message = {"clientId":client_id,"message":data}
            await socket_manager.broadcast(json.dumps(message)) # send message to for all active members
            
    except WebSocketDisconnect:
        socket_manager.disconnect(websocket) # disconnect with server
        message = {"clientId":client_id,"message":"Offline"}
        await socket_manager.broadcast(json.dumps(message))


@router.post('/create_agent')
async def create_agent(agent : AgentSchema):
    """Create a agent"""
    try:
        # check the agent has same name or not
        agent_names =[i[0] for i in db.session.query(Agents.name).filter_by(user_id=agent.user_id).all()]

        if (agent.name.rstrip()) in agent_names:
            return JSONResponse(status_code=404, content={"errorMessage":"Given name is already exists"})

        new_agent = Agents(name = agent.name.rstrip(), user_id = agent.user_id,isavailable=False)
        db.session.add(new_agent)
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message": "Agnet is successfully created!"})
    except Exception as e:
        print(e, "at creating agent. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"Can't create a agent"})

@router.get('/get_agents')
async def get_agents(user_id : int):
    """Get all agent list per user"""

    try:
        all_agents = db.session.query(Agents).filter_by(user_id=user_id).all()
        agent_list =[]
        for agent in all_agents:
            get_agent = {"id":agent.id,"name":agent.name}
            agent_list.append(get_agent)
        sorted_agents = sorted(agent_list, key=lambda agent_list: agent_list['id'],reverse = True)

        return {"agents":sorted_agents}
    except Exception as e:
        print(e, "at getting agent list. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"Can't get the list of agents"})

@router.delete('/delete_agent')
async def delete_agent(user_id:int, agent_id : int):
    """Remove(Delete) agent"""

    try:
        if (db.session.query(Agents).filter_by(id=agent_id).first()) == None:
            return JSONResponse(status_code=404,content={"errorMessage":"Can't find agent"})
        db.session.query(Agents).filter_by(user_id=user_id).filter_by(id = agent_id).delete() 
        db.session.commit()

        return JSONResponse(status_code = 200, content = {"message": "Agent removed successfully!"})
    except Exception as e:
        print(e, "at remove agent. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"Can't remove agent"})




