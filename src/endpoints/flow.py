import uuid
from ..schemas.flowSchema import *
from ..schemas.nodeSchema import *
from ..models.flow import *
from ..models.node import *

from fastapi import APIRouter, status, HTTPException , encoders
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
async def create_flow(flow : FlowSchema):
    try:
        
        if(flow.name == None or len(flow.name.strip()) == 0):
            return Response(status_code=204)
        my_uuid = uuid.uuid4()
        new_flow = Flow(name = flow.name, user_id = flow.user_id, created_at = datetime.now(timezone.utc), updated_at = datetime.now(timezone.utc),publish_token = my_uuid)
        db.session.add(new_flow)
        db.session.commit()

        flow_id = db.session.query(Flow.id).filter_by(id = new_flow.id).first()
        print(flow_id)
        
        default_node = Node(name = "Welcome", path = "special", type = "special", node_type = "start_node", properties = json.dumps({"text": ""}), position = json.dumps({"top": "100","left": "100"}),flow_id=flow_id[0])
        db.session.merge(default_node)
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
async def get_flow_list(user_id : int):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 

        flow_ids = db.session.query(Flow).filter_by(user_id = user_id).all()
        # ids = [r.id for r in db.session.query(Flow.id).filter_by(user_id = user_id).distinct()]
        ids = []
        for fl in flow_ids:
            ids.append(fl.id)
        return JSONResponse(status_code=200, content={"message": "success", "flow_ids" : ids})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get('/search_flows')
async def search_flows(user_id : int, flow_name:str):
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


@router.get('/rename_flow')
async def rename_flow(user_id : int, flow_id:str, new_name:str):
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


@router.delete('/delete_flow')
async def delete_flow(user_id : int, flow_list: List[int] ):
    user_check = await check_user_id(user_id)
    if user_check.status_code != 200 :
        return user_check 

    for flow_id in flow_list:
        if (db.session.query(Flow).filter_by(id = flow_id).first() == None):
            return JSONResponse(status_code=404, content={"message":"no flows with this id"})    
        db.session.query(Flow).filter_by(id = flow_id).delete()

    db.session.commit()
    db.session.close()
    return JSONResponse(status_code=200, content={"message":"success"})

@router.post('/duplicate_flow')
async def duplicate_flow(user_id:int, flow_id:int):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flow_data = db.session.query(Flow).filter_by(id = flow_id).first()
        if (flow_data == None):
            return JSONResponse(status_code=404, content={"message":"please check the id"})   

        new_flow = Flow(name = "duplicate of " + flow_data.name, user_id = flow_data.user_id, created_at = datetime.now(timezone.utc), updated_at = datetime.now(timezone.utc), diagram = flow_data.diagram)
        db.session.add(new_flow)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at duplcate flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.get("/get_diagram")
async def get_diagram(flow_id :int):
    all_connections = db.session.query(Node).filter_by(flow_id=flow_id).all()
    all_custom_fileds = db.session.query(Node).filter_by(flow_id=flow_id).all()
    all_nodes = db.session.query(Node).filter_by(flow_id=flow_id).all()
    sub_nodes = db.session.query(SubNode).filter_by(flow_id=flow_id).all()
    return {'diagram':{'connection':all_connections,'nodes':{'node':all_nodes,'sub_node':sub_nodes},'custom_field':all_custom_fileds}}


@router.post('/save_draft')
async def save_draft(nodes : List[NodeSchema], conns : List[ConnectionSchema], cus : List[CustomFieldSchema]):
    try:
        db.session.query(Flow).filter_by(id = nodes[0].flow_id).update({'updated_at' : datetime.now(), 'diagram' : {"nodes" : encoders.jsonable_encoder(nodes), "connections":encoders.jsonable_encoder(conns), "custom_fields": encoders.jsonable_encoder(cus)}})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.post('/publish')
async def publish(flow_id : int, user_id : int, nodes : List[NodeSchema], conns : List[ConnectionSchema], cus : List[CustomFieldSchema]):
    await save_draft(nodes,conns,cus)
    token = db.session.query(Flow.publish_token).filter_by(id = flow_id).filter_by(user_id = user_id).first()[0]
    return JSONResponse(status_code=200, content={"message":"success", "token": token})