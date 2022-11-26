import json
from fastapi import APIRouter, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import db

# from fastapi_socketio import SocketManager
from datetime import datetime
from typing import List
from ..schemas.livechatSchema import AddMember
from ..models.livechat import Account, Member
from ..models.users import UserInfo
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


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, token: str):
    print(websocket.values)
    if token != "secret":
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Please provide right token"},
        )
    await socket_manager.connect(websocket)  # connecteion eshtablish
    try:
        while True:
            data = await websocket.receive_text()  # receive message
            await socket_manager.send_personal_message(
                f"You wrote: {data}", websocket
            )  # send to private message
            message = {"clientId": client_id, "message": data}
            await socket_manager.broadcast(
                json.dumps(message)
            )  # send message to for all active members

    except WebSocketDisconnect:
        socket_manager.disconnect(websocket)  # disconnect with server
        message = {"clientId": client_id, "message": "Offline"}
        await socket_manager.broadcast(json.dumps(message))


@router.post("/add_member")
async def add_member(mail: str, member: AddMember):
    """This function is use to add a new team member"""
    try:

        if db.session.query(UserInfo.name).filter_by(email=mail).first() is not None:
            return JSONResponse(
                status_code=404,
                content={"errorMessage": "Given email is already registered"},
            )

        new_member = UserInfo(
            name=member.name.rstrip(), user_id=member.user_id, isavailable=False
        )
        db.session.add(new_member)
        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=200, content={"message": "Team member is successfully added!"}
        )
    except Exception as e:
        print(e, "at creating agent. Time:", datetime.now())
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't add a team member"}
        )


@router.get("/get_agents")
async def get_agents(user_id: int):
    """This function is use to get all member list per user"""

    try:
        members = sorted([{"id": agent.id, "name": agent.ename} for agent in db.session.query(Member).filter_by(user_id=user_id).all()],
            key=lambda members: members["id"], reverse=True
        )   

        return {"agents": members}
    except Exception as e:
        print(e, "at getting member list. Time:", datetime.now())
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't get the list of members"}
        )


@router.delete("/delete_agent")
async def delete_agent(user_id: int, agent_id: int):
    """This function is use to remove(Delete) member"""

    try:
        if (db.session.query(Member).filter_by(id=agent_id).first()) is None:
            return JSONResponse(
                status_code=404, content={"errorMessage": "Can't find member"}
            )
        db.session.query(Member).filter_by(user_id=user_id).filter_by(
            id=agent_id
        ).delete()
        db.session.commit()

        return JSONResponse(
            status_code=200, content={"message": "Member removed successfully!"}
        )
    except Exception as e:
        print(e, "at remove member. Time:", datetime.now())
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't remove member"}
        )


@router.get("/teammembers")
async def team_members(account_id: int):
    user_ids = db.session.query(Account.user_id).filter_by(id=account_id).all()
    return user_ids
