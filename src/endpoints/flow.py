from ..schemas.flowSchema import *
from ..models.flow import *


from fastapi import APIRouter, status, HTTPException
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

        new_flow = Flow(name = flow.name, user_id = flow.user_id, created_at = datetime.now(timezone.utc), updated_at = datetime.now(timezone.utc))
        db.session.add(new_flow)
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