import uuid
import boto3
import os
import collections
from fastapi import APIRouter, Depends, encoders, UploadFile, status
from fastapi.responses import JSONResponse, Response
from fastapi_sqlalchemy import db
from datetime import datetime
from typing import List, Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.models.customfields import Variable

from ..dependencies.config import SENDGRID_EMAIL

from ..dependencies.config import AWS_ACCESS_KEY, AWS_ACCESS_SECRET_KEY, BUCKET_NAME

from ..schemas.flowSchema import FlowSchema, ChatSchema
from ..models.flow import Flow, Chat, EmbedScript
from ..models.integrations import SendEmail, Slack
from ..models.node import Node, SubNode, Connections
from ..endpoints.node import check_user_token

from ..dependencies.auth import AuthHandler

auth_handler = AuthHandler()

router = APIRouter(
    prefix="/flow",
    tags=["Flow"],
    responses={404: {"description": "Not found"}},
)


async def check_user_id(user_id: int):
    """Check Flow are exists for that user"""

    try:
        if db.session.query(Flow).filter_by(user_id=user_id).first() is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't find flows for this user."},
            )
        else:
            return JSONResponse(status_code=status.HTTP_200_OK)
    except Exception as e:
        print(e, "at user verification. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "User is not exists!"},
        )


@router.post("/create_flow")
async def create_flow(flow: FlowSchema, token=Depends(auth_handler.auth_wrapper)):
    """Create a new Flow"""

    try:
        flow_names = [
            i[0]
            for i in db.session.query(Flow.name)
            .filter_by(user_id=flow.user_id)
            .filter_by(status="active")
            .all()
        ]

        if (
            flow.name.rstrip()
        ) in flow_names:  # check flow name is already present or not
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"errorMessage": "Name is already taken"},
            )

        if flow.name is None or len(flow.name.strip()) == 0:
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"errorMessage": "Please, Enter valid name!"},
            )

        add_new_flow = Flow(
            name=flow.name.rstrip(),
            user_id=flow.user_id,
            created_at=datetime.today().isoformat(),
            updated_at=datetime.today().isoformat(),
            publish_token=None,
            status="active",
            isEnable=True,
            chats=0,
            finished=0,
            workspace_id=0,
            workspace_name=None,
        )
        db.session.add(add_new_flow)
        db.session.commit()

        flow_id = db.session.query(Flow.id).filter_by(id=add_new_flow.id).first()
        node_data = [{"text": "Welcome", "button": "Start"}]

        # Add Welcome node for new Flow
        welcome_node = Node(
            name="Welcome",
            type="special",
            data=node_data,
            position={"x": 180, "y": 260},
            flow_id=flow_id[0],
            destination="",
        )
        db.session.add(welcome_node)
        db.session.commit()

        # Add Subnode for welcome node
        welcome_subnode = SubNode(
            id=str(welcome_node.id) + "_" + str(1) + "b",
            node_id=welcome_node.id,
            flow_id=welcome_node.flow_id,
            data=node_data[0],
            type=welcome_node.type,
        )
        db.session.add(welcome_subnode)
        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Flow created Successfully!"},
        )
    except Exception as e:
        print(e, "at create flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't create Flow"},
        )


@router.get("/get_flow_list")
async def get_flow_list(user_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Get the flow list by user"""

    try:
        flows = (
            db.session.query(Flow)
            .filter_by(user_id=user_id)
            .filter_by(isEnable=True)
            .all()
        )
        # get the workspace id & list
        flow_list = []
        for fl in flows:
            flow_list.append(
                {
                    "flow_id": fl.id,
                    "name": fl.name,
                    "updated_at": encoders.jsonable_encoder(fl.updated_at),
                    "created_at": encoders.jsonable_encoder(fl.created_at),
                    "chats": fl.chats,
                    "finished": fl.finished,
                    "publish_token": fl.publish_token,
                    "workspace_id": fl.workspace_id,
                    "workspace_name": fl.workspace_name,
                }
            )
        sorted_list = sorted(
            flow_list, key=lambda flow_list: flow_list["flow_id"], reverse=True
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"flows": sorted_list}
        )
    except Exception as e:
        print(e, "at getting flow list. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't find flows for this user"},
        )


@router.post("/rename_flow")
async def rename_flow(
    user_id: int, flow_id: int, new_name: str, token=Depends(auth_handler.auth_wrapper)
):
    """This function use to rename the flow"""

    try:
        flow_names = [
            i[0]
            for i in db.session.query(Flow.name)
            .filter_by(user_id=user_id)
            .filter_by(status="active")
            .all()
        ]

        if new_name in flow_names:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"errorMessage": "Name is already exists"},
            )
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user

        # check user exists or not
        user_check = await check_user_id(user_id)
        if user_check.status_code != status.HTTP_200_OK:
            return user_check

        flow_info = db.session.query(Flow).filter_by(id=flow_id)
        if flow_info.first() is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't find flow"},
            )
        else:
            flow_info.update(
                {"name": new_name, "updated_at": datetime.today().isoformat()}
            )
            db.session.commit()
            db.session.close()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Name Successfully updated!"},
            )

    except Exception as e:
        print(e, "at rename flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't change the flow name"},
        )


@router.delete("/delete_flow_list")
async def delete_flow(
    user_id: int, flow_list: List[int], token=Depends(auth_handler.auth_wrapper)
):
    """Delete one flow or multiple flows at a time"""

    try:
        for flow_id in flow_list:
            valid_user = await check_user_token(flow_id, token)
            if valid_user.status_code != status.HTTP_200_OK:
                return valid_user
        # check user existance
        user_check = await check_user_id(user_id)
        if user_check.status_code != status.HTTP_200_OK:
            return user_check

        for flow_id in flow_list:
            if db.session.query(Flow).filter_by(id=flow_id).first() is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"errorMessage": "Can't find flow"},
                )
            db.session.query(Flow).filter_by(id=flow_id).update({"status": "trashed"})

        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Flow deleted Successfully"},
        )

    except Exception as e:
        print(e, "at delete flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't delete flow"},
        )


@router.post("/duplicate_flow")
async def duplicate_flow(
    user_id: int, flow_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Create a copy(duplicate) flow with same data"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user

        # check user existance
        user_check = await check_user_id(user_id)
        if user_check.status_code != status.HTTP_200_OK:
            return user_check

        flow_data = db.session.query(Flow).filter_by(id=flow_id).first()
        if flow_data is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't find flow"},
            )
        my_uuid = uuid.uuid4()
        new_flow = Flow(
            name="duplicate of " + flow_data.name,
            user_id=flow_data.user_id,
            created_at=datetime.today().isoformat(),
            updated_at=datetime.today().isoformat(),
            diagram=flow_data.diagram,
            publish_token=my_uuid,
            status="active",
            isEnable=True,
            chats=0,
            finished=0,
        )
        db.session.add(new_flow)
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Copy of flow created"},
        )
    except Exception as e:
        print(e, "at duplcate flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't copy of this flow"},
        )


@router.get("/get_diagram")
async def get_diagram(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Get the diagram which contain all nodes, connections, sub_nodes with data"""

    try:
        flow_data = (
            db.session.query(Flow)
            .filter_by(id=flow_id)
            .filter_by(status="trashed")
            .first()
        )
        if flow_data is not None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't find flow"},
            )

        all_connections = db.session.query(Connections).filter_by(flow_id=flow_id).all()
        connections_list = []
        for conn in all_connections:
            get_conn = {
                "id": str(conn.id),
                "markerEnd": {
                    "type": "arrowclosed",
                    "color": "#79E794",
                    "orient": "auto",
                },
                "type": "buttonedge",
                "source": str(conn.source_node_id),
                "sourceHandle": conn.sub_node_id,
                "target": str(conn.target_node_id),
                "animated": True,
                "label": "edge label",
                "flow_id": flow_id,
            }
            connections_list.append(get_conn)
        all_nodes = db.session.query(Node).filter_by(flow_id=flow_id).all()
        sub_nodes = db.session.query(SubNode).filter_by(flow_id=flow_id).all()
        customfields = (
            db.session.query(Variable)
            .filter_by(
                user_id=db.session.query(Flow.user_id).filter_by(id=flow_id).first()[0]
            )
            .all()
        )

        node_list = []
        for node in all_nodes:
            sub_nodes = db.session.query(SubNode).filter_by(node_id=node.id).all()
            sub_node_list = []
            for sub_node in sub_nodes:
                fields = dict(sub_node.data.items())  # get fields of data(text,btn,...)
                my_dict = {
                    "flow_id": sub_node.flow_id,
                    "node_id": sub_node.node_id,
                    "type": sub_node.type,
                    "id": sub_node.id,
                    "data": fields,
                    "destination": node.destination,
                }
                # for key,value in fields.items():
                #     my_dict[key] = value
                sub_node_list.append(my_dict)
            sorted_sub_node_list = sorted(
                sub_node_list, key=lambda sub_node_list: sub_node_list["id"]
            )
            get_data = {
                "flow_id": flow_id,
                "id": str(node.id),
                "type": node.type,
                "position": node.position,
                "destination": node.destination,
                "data": {
                    "id": node.id,
                    "label": "NEW NODE",
                    "nodeData": sorted_sub_node_list,
                },
            }
            node_list.append(get_data)

        return {
            "nodes": node_list,
            "connections": connections_list,
            "sub_nodes:": encoders.jsonable_encoder(sub_nodes),
            "custom_fields": encoders.jsonable_encoder(customfields),
        }
    except Exception as e:
        print(e, "at getting diagram. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Cannot get diagram"},
        )


async def save_draft(flow_id: int):
    """Save the diagram in db"""

    try:
        diagram = await get_diagram(flow_id)
        for node in diagram["nodes"]:
            if node["type"] == "slack":
                if node["data"]["nodeData"][0]["data"]["slack_id"] is None:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"errorMessage": "No slack channel selected"},
                    )
        db.session.query(Flow).filter_by(id=flow_id).update({"diagram": diagram})
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Save data Successfully"},
        )
    except Exception as e:
        print(e, "at save draft. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't save draft"},
        )


async def preview(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Return the diagram for the preview (user conversion)"""

    try:
        get_diagram = db.session.query(Flow).filter_by(id=flow_id).first()
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"updated_at": datetime.today().isoformat()}
        )
        if get_diagram is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errorMessage": "Please publish the flow"},
            )
        return get_diagram.diagram

    except Exception as e:
        print(e, "at preview of flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't Preview"},
        )


@router.post("/{my_token}/preview")
async def tokenize_preview(my_token: str):
    """Return the diagram for the preview using valid token(user conversion)"""

    try:
        flow_id = db.session.query(Flow.id).filter_by(publish_token=my_token).first()[0]

        if (
            my_token
            in db.session.query(Flow.publish_token)
            .filter_by(publish_token=my_token)
            .first()[0]
        ):
            return await preview(flow_id, token=Depends(auth_handler.auth_wrapper))
        else:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"errorMessage": "Token is not valid"},
            )
    except Exception as e:
        print(e, "at token/preview. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't create preview"},
        )


@router.post("/publish")
async def publish(
    flow_id: int, diagram: Dict, token=Depends(auth_handler.auth_wrapper)
):
    """Save latest diagram with token in database and allow to publish"""

    try:
        # valid_user = await check_user_token(flow_id,token)
        # if (valid_user.status_code is not status.HTTP_200_OK):
        #     return valid_user
        save_draft_status = await save_draft(flow_id)
        if save_draft_status.status_code != status.HTTP_200_OK:
            return save_draft_status

        db_token = db.session.query(Flow.publish_token).filter_by(id=flow_id).first()[0]
        if db_token is not None:
            publish_token = db_token
        else:
            publish_token = uuid.uuid4()

        if diagram is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errorMessage": "diagram field should not be empty!"},
            )

        db.session.query(Flow).filter_by(id=flow_id).update(
            {
                "updated_at": datetime.today().isoformat(),
                "diagram": diagram,
                "publish_token": publish_token,
            }
        )
        db.session.commit()
        db.session.close()

        if token is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't found"},
            )

        return {"message": "success", "token": publish_token}
    except Exception as e:
        print(e, "at publish flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't publish"},
        )


@router.post("/disable_flow")
async def flow_disabled(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """This function is use to disable flow"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update({"isEnable": False})
        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "flow disabled"}
        )
    except Exception as e:
        print(e, "at disable flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "please check the input"},
        )


@router.patch("/archive_flow")
async def archive_flow(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Move flow into trash folder"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"isEnable": False, "status": "trashed"}
        )
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"workspace_id": 0, "workspace_name": None}
        )
        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "flow moved into trash folder"},
        )
    except Exception as e:
        print(e, "at archive flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "please check the input"},
        )


@router.get("/get_trashed_flows")
async def get_trashed_flows(user_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Get the list of flows which in trash folder"""

    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != status.HTTP_200_OK:
            return user_check

        flows = (
            db.session.query(Flow)
            .filter_by(user_id=user_id)
            .filter_by(status="trashed")
            .all()
        )
        flow_list = []
        for fl in flows:
            flow_list.append(
                {
                    "flow_id": fl.id,
                    "name": fl.name,
                    "updated_at": encoders.jsonable_encoder(fl.updated_at),
                    "created_at": encoders.jsonable_encoder(fl.created_at),
                    "chats": fl.chats,
                    "finished": fl.finished,
                    "publish_token": fl.publish_token,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"flows": flow_list}
        )
    except Exception as e:
        print(e, "at getting trashed flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "please check the input"},
        )


@router.delete("/trash/delete_forever")
async def complete_delete_flow(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Delete permanently flow"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).filter_by(
            isEnable=False
        ).filter_by(status="trashed").delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "success"}
        )
    except Exception as e:
        print(e, "at delete_forever. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "please check the input"},
        )


@router.post("/trash/restore_flow")
async def restore_flow(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Restore any flow and use it"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update(
            {
                "status": "active",
                "isEnable": True,
                "updated_at": datetime.today().isoformat(),
            }
        )
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "success"}
        )
    except Exception as e:
        print(e, "at restore flow. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "please check the input"},
        )


@router.get("/flow_detail")
async def get_flow_detail(flow_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Get flow details name and publish_token"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        db_name = db.session.query(Flow).filter_by(id=flow_id).first()
        token = db.session.query(Flow.publish_token).filter_by(id=flow_id).first()[0]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"name": db_name.name, "publish_token": token},
        )
    except Exception as e:
        print(e, "at flow details. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't found"},
        )


async def post_message(slack_id, message):
    """Send the message to the slack channel"""

    slack_db = db.session.query(Slack).filter_by(id=slack_id).first()
    client = WebClient(token=slack_db.bot_token)
    try:
        response = client.chat_postMessage(channel=slack_db.channel_name, text=message)
        assert response["message"]["text"] == message
    except SlackApiError as e:
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")


async def send_email(data):
    """Send Email by user to customers"""

    try:
        if not data["customEmail"]:
            message = Mail(
                from_email=SENDGRID_EMAIL,
                to_emails=data["to_email"],
                subject=data["subject"],
                html_content="<p>" + data["text"] + "</p>",
            )
            try:
                send_mail = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
                send_mail.send(message)
            except Exception as e:
                print(e, "at sending email. Time:", datetime.now())
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"errorMessage": "API is not working"},
                )
        else:
            message = Mail(
                from_email=db.session.query(SendEmail.from_email)
                .filter_by(id=data["frome_email"])
                .first(),
                to_emails=data["to_email"],
                subject=data["subject"],
                html_content="<p>" + data["text"] + "</p>",
            )
            try:
                send_mail = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
                send_mail.send(message)
            except Exception as e:
                print(e, "at sending email. Time:", datetime.now())
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"errorMessage": "API is not working"},
                )
    except Exception as e:
        print(e, "at sending email. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Can't send email"},
        )


@router.post("/save_chat_history")
async def save_chat_history(
    chats: ChatSchema, token=Depends(auth_handler.auth_wrapper)
):
    """Save the chat history of every user"""

    try:
        valid_user = await check_user_token(chats.flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        get_visitor = (
            db.session.query(Chat)
            .filter_by(visitor_ip=chats.visitor_ip)
            .filter_by(flow_id=chats.flow_id)
            .first()
        )

        if get_visitor is not None:
            # published_nodes = []
            # for i in flow_info['diagram']['nodes']:
            #     published_nodes.append(i['id'])
            saved_nodes = []
            for i in chats.chat:
                saved_nodes.append(i["node_id"])
            # if(finish_count[0] == None):
            #     finish = 0
            # else:
            #     finish = len(set(saved_nodes))
            # increase count of finished initialized
            # if len(set(published_nodes)) == len(set(saved_nodes)):
            #     finish = finish + 1
            # else:
            #     finish = finish
            # db.session.query(Flow).filter_by(id = chats.flow_id)
            # .update({"finished":finish})
            for ch in chats.chat:
                if ch["type"] == "slack":
                    await post_message(int(ch["data"]["slack_id"]), ch["data"]["text"])
                else:
                    pass
            for ch in chats.chat:
                if ch["type"] == "send_email":
                    await send_email(ch["data"])
                else:
                    pass
            db.session.query(Chat).filter_by(visitor_ip=chats.visitor_ip).filter_by(
                flow_id=chats.flow_id
            ).update({"chat": chats.chat})
        else:
            chat_count = (
                db.session.query(Flow.chats).filter_by(id=chats.flow_id).first()
            )  # can keep this same

            if chat_count[0] is None:
                chat = 0
            else:
                chat = chat_count[0]

            # increase count of chats initialized
            chat = chat + 1

            # published_nodes = []
            # for i in flow_info['diagram']['nodes']:
            #     published_nodes.append(i['id'])

            saved_nodes = []

            for i in chats.chat:
                saved_nodes.append(i["node_id"])
            # if(finish_count[0] == None):
            #     finish = 0
            # else:
            #     finish = finish_count[0]
            # increase count of finished initialized
            # if len(set(published_nodes)) == len(set(saved_nodes)):
            #     finish = finish + 1
            # else:
            #     finish = finish
            db.session.query(Flow).filter_by(id=chats.flow_id).update({"chats": chat})
            for ch in chats.chat:
                if ch["type"] == "slack":
                    await post_message(int(ch["data"]["slack_id"]), ch["data"]["text"])
                else:
                    pass
            for ch in chats.chat:
                if ch["type"] == "send_email":
                    await send_email(ch["data"])
                else:
                    pass
            visitor_token = uuid.uuid4()  # create customer token for new user
            new_chat = Chat(
                flow_id=chats.flow_id,
                visited_at=datetime.today().isoformat(),
                updated_at=datetime.today().isoformat(),
                chat=chats.chat,
                visitor_ip=chats.visitor_ip,
                visitor_token=visitor_token,
            )
            db.session.add(new_chat)

        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "Success"}
        )
    except Exception as e:
        print(e, "at save chat history. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Error in save chat history"},
        )


@router.get("/get_chat_history")
async def get_chat_history(ip: str, token: str):
    """Get the chat history of every user"""

    try:
        flow_id = db.session.query(Flow.id).filter_by(publish_token=token).first()
        chat_history = (
            db.session.query(Chat)
            .filter_by(visitor_ip=ip)
            .filter_by(flow_id=flow_id[0])
            .first()
        )
        if chat_history is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Can't find ip address"},
            )
        chat_data = {"chat": chat_history.chat, "flow_id": chat_history.flow_id}
        return JSONResponse(status_code=status.HTTP_200_OK, content=chat_data)
    except Exception as e:
        print(e, "at get chat history. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Can't find chat history"},
        )


@router.post("/upload")
async def upload_file_to_s3(flow_id: int, file: UploadFile):
    """Upload the html file into s3 bucket"""
    try:

        s3 = boto3.resource(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_ACCESS_SECRET_KEY,
        )
        bucket = s3.Bucket(BUCKET_NAME)
        bucket.upload_fileobj(
            file.file,
            "embedfile/" + str(flow_id) + "/" + (file.filename),
            ExtraArgs={"ContentType": "text/html"},
        )

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com\
            /embedfile/{flow_id}/{file.filename}"

        db_file = EmbedScript(
            file_name=file.filename,
            created_at=datetime.today().isoformat(),
            file_url=s3_file_url,
        )
        db.session.add(db_file)
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "Success"}
        )
    except Exception as e:
        print(e, "at upload file to s3. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Error at uploading file"},
        )


@router.post("/upload_user")
async def upload_file_from_user(flow_id: int, file: UploadFile):
    """Upload the html file into s3 bucket"""

    try:

        s3 = boto3.resource(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_ACCESS_SECRET_KEY,
        )
        bucket = s3.Bucket(BUCKET_NAME)
        bucket.upload_fileobj(
            file.file,
            "visitorfiles/" + str(flow_id) + "/" + (file.filename),
            ExtraArgs={"ContentType": "text/html"},
        )

        # S3_url
        # f"https://{BUCKET}.s3.ap-south-1.amazonaws.com/visitorfiles/{flowid}/{filename}"
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "Success"}
        )
    except Exception as e:
        print(e, "at uplode html file. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorMessage": "Error at uploading file"},
        )


@router.get("/flow_analysis")
async def get_flow_analysis_data(
    flow_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Get the analysis for flow
    Details: This analysis shows how many visitors visit this flow
    and which path they choose (how conversion goes) in percentage"""

    try:
        valid_user = await check_user_token(flow_id, token)
        if valid_user.status_code != status.HTTP_200_OK:
            return valid_user
        diagram = await get_diagram(flow_id)
        connections = diagram["connections"]
        total_visits = len(db.session.query(Chat).filter_by(flow_id=flow_id).all())
        if total_visits == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "There is no visitors!"},
            )
        chat_data = db.session.query(Chat.chat).filter_by(flow_id=flow_id).all()
        subnode_list = []
        input_types = ["url", "file", "text", "number", "phone", "email", "date"]
        pop_list = []

        for i in range(len(chat_data)):
            if len(chat_data[i][0]) == 0:
                total_visits -= 1
            else:
                if chat_data[i][0][-1]["type"] in input_types:
                    pop_list.append(chat_data[i][0][-1]["id"])
                else:
                    pop_list
                id_list = []
                for i in chat_data[i][0]:
                    if i["type"] == "button":
                        id_list.append(i["id"])
                    elif "from" in i:
                        pass
                    elif i["id"] in pop_list:
                        pass
                    else:
                        id_list.append(i["id"])
                subnode_list.extend(list(set(id_list)))

        subnode_set = list(set(subnode_list))
        subnode_frequency = dict(collections.Counter(subnode_list))

        for conn in connections:
            if conn["sourceHandle"] in subnode_set:
                n = subnode_frequency[conn["sourceHandle"]]
                if round(n / total_visits * 100) == 100:
                    conn["data"] = {"n": n, "percentage": "100%", "color": "#006400"}
                else:
                    conn["data"] = {
                        "n": n,
                        "percentage": str(round(n / total_visits * 100)) + "%",
                        "color": "#0000FF",
                    }
            else:
                conn["data"] = {"n": 0, "percentage": "0" + "%", "color": "#ff0000"}

        return {"nodes": diagram["nodes"], "connections": connections}
    except Exception as e:
        print(e, "at flow analysis. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "There is no visitors!"},
        )


@router.post("/upload_from_user")
async def upload_to_s3_from_user(file: UploadFile, node_id: int, flow_id: int):
    """Upload files at conversion time by user which store in s3 bucket"""

    try:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_ACCESS_SECRET_KEY,
        )
        bucket = s3.Bucket(BUCKET_NAME)

        if (
            db.session.query(Node)
            .filter_by(id=node_id)
            .filter_by(flow_id=flow_id)
            .first()
            is None
        ):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"errorMessage": "Node not found"},
            )

        CONTENT_TYPES = [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "video/mp4",
            "text/html",
            "image/svg+xml",
            "text/plain",
            "application/msword",
            "application/pdf",
            "audio/mpeg",
            "text/csv",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        if file.content_type in CONTENT_TYPES:
            bucket.upload_fileobj(
                file.file,
                "userfiles/"
                + str(flow_id)
                + "/"
                + str(node_id)
                + "/"
                + (file.filename),
                ExtraArgs={"ContentType": file.content_type},
            )

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com\
            /userfiles/{flow_id}/{node_id}/{file.filename}"
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Successfully Uploaded", "url": s3_file_url},
        )
    except Exception as e:
        print(e, "at upload from user. Time:", datetime.now())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"errorMessage": "Error at uploading"},
        )
