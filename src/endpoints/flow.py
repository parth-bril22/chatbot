
import uuid

from ..schemas.flowSchema import *
from ..schemas.nodeSchema import *
from ..models.flow import *
from ..models.node import *
from ..models.users import *
from src.endpoints.node import preview

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

from fastapi import APIRouter, Depends , encoders
from fastapi.responses import JSONResponse, Response
from fastapi_sqlalchemy import db
import json
from datetime import timezone, datetime
from typing import List

router = APIRouter(
    prefix="/flow",
    tags=["Flow"],
    responses={404: {"description": "Not found"}},
)

@router.post('/create_flow')
async def create_flow(flow : FlowSchema,token = Depends(auth_handler.auth_wrapper)):
    try:
        if(flow.name == None or len(flow.name.strip()) == 0):
            return Response(status_code=204)
        new_flow = Flow(name = flow.name, user_id = flow.user_id, created_at = datetime.now(timezone.utc), updated_at = datetime.now(timezone.utc),publish_token=None,status = "active", isEnable = True,chats =0, finished=0)
        db.session.add(new_flow)
        db.session.commit()

        flow_id = db.session.query(Flow.id).filter_by(id = new_flow.id).first()
        print(flow_id)
        node_data = []
        node_data.append({"text": "Welcome","button":"Start"})
        default_node = Node(name = "Welcome", type = "special", data = node_data, position = {"x": "180","y": "260"},flow_id=flow_id[0])
        db.session.add(default_node)
        db.session.commit()
        chat_subnode = SubNode(id = str(default_node.id) + "_" + str(1) + "b", node_id = default_node.id, flow_id = default_node.flow_id, data = node_data[0], type = "chat")
        btn_subnode = SubNode(id = str(default_node.id) + "_" + str(2) + "b", node_id = default_node.id, flow_id = default_node.flow_id, data = node_data[1], type = "button")
        db.session.add(chat_subnode)
        db.session.add(btn_subnode)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


async def check_user_id(user_id:str):
    try:
        if(db.session.query(Flow).filter_by(user_id = user_id).first() == None):
            return JSONResponse(status_code=404, content={"message":"no flows at this id"})
        else:
            return JSONResponse(status_code=200)
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the user id input"})


@router.get('/get_flow_list')
async def get_flow_list(user_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 

        flows = db.session.query(Flow).filter_by(user_id = user_id).filter_by(isEnable = True).all()
        flow_list = []
        for fl in flows:
            flow_list.append({"flow_id":fl.id, "name":fl.name, "updated_at":encoders.jsonable_encoder(fl.updated_at),"created_at":encoders.jsonable_encoder(fl.created_at), "chats":fl.chats,"finished":fl.finished, "publish_token":fl.publish_token})
        return JSONResponse(status_code=200, content={"flows" : flow_list})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get('/search_flows')
async def search_flows(user_id : int, flow_name:str,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flows = db.session.query(Flow).filter_by(name = flow_name).all()
        if(len(flows) == 0):
            return JSONResponse(status_code=404, content={"message":"no flows with this name"})
        else:
            flows_lst = []
            for fl in flows:
                flows_lst.append(fl.id)
            return JSONResponse(status_code=200, content={"message": "success", "flow_ids" : flows_lst})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.post('/rename_flow')
async def rename_flow(user_id : int, flow_id:str, new_name:str,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flows = db.session.query(Flow).filter_by(id = flow_id)
        if(flows.first() == None):
            return JSONResponse(status_code=404, content={"message":"no flows with this name"})
        else:
            flows.update({'name' : new_name})
            db.session.commit()
            db.session.close()
            return JSONResponse(status_code=200, content={"message": "success"})
            
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.delete('/delete_flow_list')
async def delete_flow(user_id : int, flow_list: List[int],token = Depends(auth_handler.auth_wrapper) ):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200:
            return user_check

        for flow_id in flow_list:
            if (db.session.query(Flow).filter_by(id=flow_id).first() == None):
                return JSONResponse(status_code=404, content={"message": "no flows with this id"})
            db.session.query(Flow).filter_by(id=flow_id).update({"status": "trashed"})

        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})

    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.post('/duplicate_flow')
async def duplicate_flow(user_id:int, flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flow_data = db.session.query(Flow).filter_by(id = flow_id).first()
        if (flow_data == None):
            return JSONResponse(status_code=404, content={"message":"please check the id"})   
        my_uuid = uuid.uuid4()
        new_flow = Flow(name = "duplicate of " + flow_data.name, user_id = flow_data.user_id, created_at = datetime.now(timezone.utc), updated_at = datetime.now(timezone.utc), diagram = flow_data.diagram, publish_token=my_uuid,status = "active", isEnable = True, chats = 0, finished = 0)
        db.session.add(new_flow)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at duplcate flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get("/get_diagram")
async def get_diagram(flow_id :int,token = Depends(auth_handler.auth_wrapper)):
    try:
        # check the status of the flow 
        flow_data = db.session.query(Flow).filter_by(id=flow_id).filter_by(status="trashed").first()

        if (flow_data != None):
            return JSONResponse(status_code=201,content={"message":"flow is not found"})
        
        all_connections = db.session.query(Connections).filter_by(flow_id=flow_id).all()
        cons =[]
        for con in all_connections:
            get_con = {"id": con.id, "markerEnd": {"type": "MarkerType.ArrowClosed",},"type": 'buttonedge', "source": con.source_node_id, "sourceHandle": con.sub_node_id,"target": con.target_node_id, "animated": True, "label": 'edge label', "flow_id":flow_id}
            cons.append(get_con)
        all_custom_fileds = db.session.query(CustomFields).filter_by(flow_id=flow_id).all()
        all_nodes = db.session.query(Node).filter_by(flow_id=flow_id).all()
        sub_nodes = db.session.query(SubNode).filter_by(flow_id=flow_id).all()
        get_list = []
        for node in all_nodes:
            sub_nodes = db.session.query(SubNode).filter_by(node_id = node.id).all()
            sn = []
            for sub_node in sub_nodes:
                fields = dict(sub_node.data.items())#get fields of data(text,btn,...)
                my_dict = {"flow_id":sub_node.flow_id, "node_id":sub_node.node_id,"type":sub_node.type,"id":sub_node.id}
                for key,value in fields.items():
                    my_dict[key] = value
                sn.append(my_dict)
            get_data = {"flow_id" : flow_id,"id": node.id, "type": node.type, "position": node.position,
             "data": { "id": node.id,"label": "NEW NODE", "nodeData": sn}}
            get_list.append(get_data)
        # return {"nodes":list({"id" : node.id, "type" : node.type, "position":node.position, "data": {"label" : "NEW NODE", "nodeData":node.data} }),"connections":encoders.jsonable_encoder(all_connections),"Custom Fields": encoders.jsonable_encoder(all_custom_fileds), "Sub Nodes:" : encoders.jsonable_encoder(sub_nodes) }
        return {"nodes": get_list,"connections": cons, "custom_fields": encoders.jsonable_encoder(all_custom_fileds),"sub_nodes:": encoders.jsonable_encoder(sub_nodes)}
    except Exception as e:
        print(e, ": at get diagram")
        return JSONResponse(status_code=400, content={"message": "Cannot get diagram"})


@router.post('/save_draft')
async def save_draft(flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        diagram = await get_diagram(flow_id)
        # print(diagram)
        db.session.query(Flow).filter_by(id = flow_id).update({'updated_at' : datetime.now(), 'diagram' : diagram})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})
 
@router.post('/{my_token}/preview')
async def tokenize_preview(my_token:str,token = Depends(auth_handler.auth_wrapper)):
    try:
        flow_id =  db.session.query(Flow.id).filter_by(publish_token = my_token).first()[0]

        if(my_token in db.session.query(Flow.publish_token).filter_by(publish_token = my_token).first()[0]):
            return await preview(flow_id, token = Depends(auth_handler.auth_wrapper))
        else:
            return JSONResponse(status_code = 404, content={"message":"Cannot open preview. Token not identified"})
    except Exception as e:
        print("Error: in  my_token/preview", e)
        return JSONResponse(status_code = 404, content={"message":"Cannot open preview"})
    
@router.post('/publish')
async def publish(flow_id: int,diagram : Dict,token = Depends(auth_handler.auth_wrapper)):
    try:
        save_draft_status = await save_draft(flow_id)
        if (save_draft_status.status_code != 200):
            return save_draft_status

        # create token
        my_uuid = uuid.uuid4()
        if (diagram ==None):
            return JSONResponse(status_code=404, content={"message": "diagram field is empty!!"})

        #get the diagram and update the diagram in flow table
        db.session.query(Flow).filter_by(id = flow_id).update({'updated_at' : datetime.now(), 'diagram' : diagram,'publish_token': my_uuid})
        db.session.commit()
        db.session.close()

        if (token == None):
            return JSONResponse(status_code=404, content={"message": "Cannot publish. Check flow_id entered"})

        return {"message": "success", "token": my_uuid}
    except Exception as e:
        print("Error in publish: ", e)
        return JSONResponse(status_code=400, content={"message": "Cannot publish"})

@router.post("/disable_flow")
async def flow_disabled(flow_id: int,user_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"isEnable": False, "updated_at": datetime.now(timezone.utc)})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "flow disabled"})
    except Exception as e:
        print("Error at disable_flow: ", e)
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.patch('/archive_flow')
async def archive_flow(flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"isEnable": False, "status": "trashed", "updated_at": datetime.now(timezone.utc)})

        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200,content={"message" : "flow moved into trash folder"})
    except Exception as e:
        print("Error at archive flow: ", e)
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.get('/get_trashed_flows')
async def get_trashed_flows(user_id: int,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 

        flows = db.session.query(Flow).filter_by(user_id = user_id).filter_by(status = "trashed").all()
        flow_list = []
        for fl in flows:
            flow_list.append({"flow_id":fl.id, "name":fl.name, "updated_at":encoders.jsonable_encoder(fl.updated_at),"created_at":encoders.jsonable_encoder(fl.created_at), "chats":fl.chats,"finished":fl.finished, "publish_token":fl.publish_token})
        return JSONResponse(status_code=200, content={"flows" : flow_list})
    except Exception as e:
        print("Error at get_trashed_flows: ", e)
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.delete('/trash/delete_forever')
async def delete_flow(flow_id: int,token = Depends(auth_handler.auth_wrapper)):
    try:
        db.session.query(Flow).filter_by(id=flow_id).filter_by(isEnable=False).filter_by(status="trashed").delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print("Error at delete_forever: ", e)
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.post('/trash/restore_flow')
async def restore_flow(flow_id: int,token = Depends(auth_handler.auth_wrapper)):
    try:
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"status": "active", "isEnable": True, "updated_at": datetime.now(timezone.utc)})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print("Error at restore: ", e)
        return JSONResponse(status_code=400, content={"message": "please check the input"})


@router.get("/flow_detail")
async def get_flow_detail(flow_id:int):
    try:
        db_name =  db.session.query(Flow).filter_by(id=flow_id).first()
        token = db.session.query(Flow.publish_token).first()[0]
        return JSONResponse(status_code=200,content={"name":db_name.name,"publish_token":token})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"message":"something is wrong"})