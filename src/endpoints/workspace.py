from sqlalchemy import JSON
from src.schemas.flowSchema import *
from ..schemas.nodeSchema import *
from ..schemas.workspaceSchema import *
from ..models.flow import Flow
from ..models.workspace import Worksapce
from fastapi.responses import JSONResponse
from ..endpoints.flow import check_user_id


from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

from fastapi import APIRouter,Depends, encoders
import datetime
from fastapi_sqlalchemy import db

router = APIRouter(
    prefix="/workspaces/v1",
    tags=["Workspaces"],
    responses={404: {"description": "Not found"}},
)

@router.post('/create_workspace')
async def create_workspace(space : WorkSpaceSchema,token = Depends(auth_handler.auth_wrapper)):
    try:
        new_wksp = Worksapce(name = space.name, user_id = space.user_id, deleted = False)
        db.session.add(new_wksp)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.get('/get_workspace')
async def create_workspace(user_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:
        all_ws = db.session.query(Worksapce).filter_by(user_id=user_id).filter_by(deleted=False).all()
        ws =[]
        for workspace in all_ws:
            get_workspace = {"id":workspace.id,"name":workspace.name}
            ws.append(get_workspace)
        return {"workspace":ws}
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get('/get_workspace_flow_list')
async def create_workspace(user_id:int,workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 

        if (db.session.query(Worksapce).filter_by(id=workspace_id).first()) == True:
            return JSONResponse(status_code=404,content={"message":"workspace not found"})

        flows = db.session.query(Flow).filter_by(user_id = user_id).filter_by(workspace_id = workspace_id).all()
        flow_list = []
        for fl in flows:
            flow_list.append({"flow_id":fl.id, "name":fl.name, "updated_at":encoders.jsonable_encoder(fl.updated_at),"created_at":encoders.jsonable_encoder(fl.created_at), "chats":fl.chats,"finished":fl.finished, "publish_token":fl.publish_token})
        return JSONResponse(status_code=200, content={"flows" : flow_list})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.post('/move_flow')
async def move_flow(flow_id:int, workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:
        db.session.query(Flow).filter_by(id=flow_id).update({'workspace_id': workspace_id})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})



@router.delete('/remove_workspace')
async def remove_workspace(user_id:int, workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:

        db.session.query(Worksapce).filter_by(user_id=user_id).filter_by(id = workspace_id).update({"deleted":True})  
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.patch('/remove_from_workspace')
async def remove_workspace(user_id:int, flow_id : int,token = Depends(auth_handler.auth_wrapper)):
    try:

        db.session.query(Flow).filter_by(user_id=user_id).filter_by(id = flow_id).update({"workspace_id":0})  
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})
# @router.post('/trash/delete_forever')
# async def delete_workspace(wksp_id : int):
#     try:

#         db.session.query(Trash).filter_by(wksp_id=wksp_id).delete()
#         db.session.commit()
#         db.session.close()
#         return JSONResponse(status_code = 200, content = {"message": "success"})
#     except Exception as e:
#         print(e, "Error: at create_flow. Time:", datetime.datetime.now())
#         return JSONResponse(status_code=400, content={"message":"please check the input"})

# @router.post('/trash/restore')
# async def restore_workspace(user_id:int, wksp_id : int):
#     try:

#         db.session.query(Worksapce).filter_by(user_id=user_id).filter_by(id = wksp_id).update({"deleted":False})
#         db.session.query(Trash).filter_by(wksp_id = wksp_id).delete()
#         db.session.commit()
#         db.session.close()
#         return JSONResponse(status_code = 200, content = {"message": "success"})
#     except Exception as e:
#         print(e, "Error: at create_flow. Time:", datetime.datetime.now())
#         return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.patch('/rename_workspace')
async def rename_workspace(user_id : int, workspace_id:str, new_name:str,token = Depends(auth_handler.auth_wrapper)):
    try:
       
        wksp = db.session.query(Worksapce).filter_by(id = workspace_id)
        if(wksp.first() == None):
            return JSONResponse(status_code=404, content={"message":"no flows with this name"})
        else:
            wksp.update({'name' : new_name})
            db.session.commit()
            db.session.close()
            return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})
