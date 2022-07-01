from fastapi import APIRouter,Depends, encoders
from datetime import datetime,timezone
from fastapi_sqlalchemy import db

from ..schemas.workspaceSchema import WorkSpaceSchema
from ..models.flow import Flow
from ..models.users import User
from ..models.workspace import Workspace
from fastapi.responses import JSONResponse
from ..endpoints.flow import check_user_id

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/workspaces/v1",
    tags=["Workspaces"],
    responses={404: {"description": "Not found"}},
)

async def check_user_token(workspace_id:int,token=Depends(auth_handler.auth_wrapper)):
    """
    Check user has rights to change worksapce functinality using token
    """
    try:
       get_user_id = db.session.query(User).filter_by(email=token).first()  
       workspace_ids = [i[0] for i in db.session.query(Workspace.id).filter_by(user_id=get_user_id.id).all()]
       if workspace_id in workspace_ids:
           return JSONResponse(status_code=200,content={"message":"workspace is exists"})
       else:
           return JSONResponse(status_code=404,content={"message":"workspace not exists for this user"})
    except Exception as e:
        print(e,"at:",datetime.now())
        return JSONResponse(status_code=400,content={"message":"please check input"})

@router.post('/create_workspace')
async def create_workspace(space : WorkSpaceSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Create a workspace as per requirements
    """
    try:
        new_workspace = Workspace(name = space.name, user_id = space.user_id, deleted = False)
        db.session.add(new_workspace)
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get('/get_workspace')
async def create_workspace(user_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get all workspaces list per user
    """
    try:
        all_workspaces = db.session.query(Workspace).filter_by(user_id=user_id).filter_by(deleted=False).all()
        workspace_list =[]
        for workspace in all_workspaces:
            get_workspace = {"id":workspace.id,"name":workspace.name}
            workspace_list.append(get_workspace)

        return {"workspace":workspace_list}
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.get('/get_workspace_flow_list')
async def create_workspace(user_id:int,workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get list of flows which are stored in workspace
    """
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 

        if (db.session.query(Workspace).filter_by(id=workspace_id).first()) == None:
            return JSONResponse(status_code=404,content={"message":"workspace not found"})

        flows = db.session.query(Flow).filter_by(user_id = user_id).filter_by(workspace_id = workspace_id).all()
        flow_list = []
        for fl in flows:
            flow_list.append({"flow_id":fl.id, "name":fl.name, "updated_at":encoders.jsonable_encoder(fl.updated_at),"created_at":encoders.jsonable_encoder(fl.created_at), "chats":fl.chats,"finished":fl.finished, "publish_token":fl.publish_token,"workspace_id":fl.workspace_id,"workspace_name":fl.workspace_name})
        return JSONResponse(status_code=200, content={"flows" : flow_list})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.post('/move_flow')
async def move_flow(flow_id:int, workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Move flow into selected workspace
    """
    try:
        if (db.session.query(Flow).filter_by(id=flow_id).first()) == None:
            return JSONResponse(status_code=404,content={"message":"Flow not found"})
        db_workspace_name = db.session.query(Workspace.name).filter_by(id=workspace_id).first()
        db.session.query(Flow).filter_by(id=flow_id).update({"workspace_id":workspace_id,"workspace_name": db_workspace_name.name})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})



@router.delete('/remove_workspace')
async def remove_workspace(user_id:int, workspace_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Delete workspace
    """
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        if (db.session.query(Workspace).filter_by(id=workspace_id).first()) == None:
            return JSONResponse(status_code=404,content={"message":"workspace not found"})
        db.session.query(Workspace).filter_by(user_id=user_id).filter_by(id = workspace_id).update({"deleted":True}) 
        db.session.commit()

        # get the all flows from the table 
        get_flow_ids = db.session.query(Flow.id).filter_by(workspace_id=workspace_id).all()
        for id in get_flow_ids:
            db.session.query(Flow).filter_by(id=id[0]).update({"workspace_id":0,'workspace_name': None})
            db.session.commit()
            db.session.close()
       
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})


@router.patch('/remove_from_workspace')
async def remove_workspace(user_id:int, flow_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Remove flow from selected workspace
    """
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        db.session.query(Flow).filter_by(user_id=user_id).filter_by(id = flow_id).update({"workspace_id":0,'workspace_name': None})  
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "Error: at create_flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})

@router.patch('/rename_workspace')
async def rename_workspace(user_id : int, workspace_id:int, new_name:str,token = Depends(auth_handler.auth_wrapper)):
    """
    Rename selected workspace
    """
    try:
        db_workspace = db.session.query(Workspace).filter_by(id = workspace_id)
        if(db_workspace.first() == None):
            return JSONResponse(status_code=404, content={"message":"no flows with this name"})
        else:
            db_workspace.update({'name' : new_name})
            get_flow_ids = db.session.query(Flow.id).filter_by(workspace_id=workspace_id).all()
            for id in get_flow_ids:
                db.session.query(Flow).filter_by(id=id[0]).update({'workspace_name': new_name})
            db.session.commit()
            db.session.close()
            return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"message":"please check the input"})
