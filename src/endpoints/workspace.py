import logging
from fastapi import APIRouter, Depends, encoders
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.workspaceSchema import WorkSpaceSchema
from ..models.flow import Flow
from ..models.users import UserInfo
from ..models.workspace import Workspace
from fastapi.responses import JSONResponse
from ..endpoints.flow import check_user_id

from ..dependencies.auth import AuthHandler

auth_handler = AuthHandler()

logger = logging.getLogger(__file__)

router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
    responses={404: {"description": "Not found"}},
)


async def check_user_token(workspace_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Check authorization of user"""

    try:
        get_user_id = db.session.query(UserInfo).filter_by(email=token).first()
        workspace_ids = [
            i[0]
            for i in db.session.query(Workspace.id)
            .filter_by(user_id=get_user_id.id)
            .all()
        ]
        if workspace_id in workspace_ids:
            return JSONResponse(
                status_code=200, content={"message": "Workspace is exists"}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"errorMessage": "Can't find Workspace for this user"},
            )
    except Exception as e:
        logger.error(f"Failed to checking authorization. ERROR: {e}")
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't give permission"}
        )


@router.post("/create_workspace")
async def create_workspace(
    space: WorkSpaceSchema, token=Depends(auth_handler.auth_wrapper)
):
    """Create a workspace"""

    try:
        # check the workspace has same name or not
        workspace_names = [
            i[0]
            for i in db.session.query(Workspace.name)
            .filter_by(user_id=space.user_id)
            .all()
        ]

        if (space.name.rstrip()) in workspace_names:
            return JSONResponse(
                status_code=404,
                content={"errorMessage": "Given name is already exists"},
            )

        new_workspace = Workspace(name=space.name.rstrip(), user_id=space.user_id)
        db.session.add(new_workspace)
        db.session.commit()
        db.session.close()

        return JSONResponse(
            status_code=200, content={"message": "Workspace is successfully created!"}
        )
    except Exception as e:
        logger.error(f"Failed to creating workspace. ERROR: {e}")
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't create a workspace"}
        )


@router.get("/get_workspace")
async def get_workspace(user_id: int, token=Depends(auth_handler.auth_wrapper)):
    """Get all workspaces list per user"""

    try:
        workspace_list = sorted(
            [
                {"id": i.id, "name": i.name}
                for i in db.session.query(Workspace).filter_by(user_id=user_id).all()
            ],
            key=lambda workspace_list: workspace_list["id"],
            reverse=True,
        )

        return {"workspace": workspace_list}
    except Exception as e:
        logger.error(f"Failed to getting workspace list. ERROR: {e}")
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't get the list of workspace"}
        )


@router.get("/get_workspace_flow_list")
async def get_workspace_flow_list(
    user_id: int, workspace_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Get list of flows which are stored in workspace"""

    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200:
            return user_check

        if (db.session.query(Workspace).filter_by(id=workspace_id).first()) is None:
            return JSONResponse(
                status_code=404, content={"errorMessage": "Can't find the workspace"}
            )

        flow_list = sorted(
            [
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
                for fl in db.session.query(Flow)
                .filter_by(user_id=user_id)
                .filter_by(workspace_id=workspace_id)
                .all()
            ],
            key=lambda flow_list: flow_list["flow_id"],
            reverse=True,
        )

        return JSONResponse(status_code=200, content={"flows": flow_list})
    except Exception as e:
        logger.error(f"Failed to get flows stored in workspace. ERROR: {e}")
        return JSONResponse(
            status_code=400,
            content={"errorMessage": "Can't get the flows from workspace"},
        )


@router.post("/move_flow")
async def move_flow(
    flow_id: int, workspace_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Move flow into selected workspace"""

    try:
        flow_info = db.session.query(Flow).filter_by(id=flow_id).first()
        if flow_info is None:
            return JSONResponse(
                status_code=404, content={"errorMessage": "Can't found flow"}
            )

        if flow_info.workspace_id == workspace_id:
            return JSONResponse(
                status_code=208,
                content={"errorMessage": "Flow is already in workspace"},
            )

        db_workspace_name = (
            db.session.query(Workspace.name).filter_by(id=workspace_id).first()
        )
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"workspace_id": workspace_id, "workspace_name": db_workspace_name.name}
        )
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=200, content={"message": "Flow move successfully!"}
        )
    except Exception as e:
        logger.error(f"Failed to moving flow. ERROR: {e}")
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't move flow from workspace"}
        )


@router.delete("/remove_workspace")
async def remove_workspace(
    user_id: int, workspace_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Remove(Delete) workspace"""

    try:
        db_query = (
            db.session.query(Workspace)
            .filter_by(id=workspace_id)
            .filter_by(id=workspace_id)
            .first()
        )
        if db_query is None:
            return JSONResponse(
                status_code=404, content={"errorMessage": "Can't find workspace"}
            )
        db_query.delete()
        db.session.commit()

        [
            db.session.query(Flow)
            .filter_by(id=id[0])
            .update({"workspace_id": 0, "workspace_name": None})
            for id in db.session.query(Flow.id)
            .filter_by(workspace_id=workspace_id)
            .all()
        ]
        db.session.commit()

        return JSONResponse(
            status_code=200, content={"message": "Workspace removed successfully!"}
        )
    except Exception as e:
        logger.error(f"Failed to removing workspace. ERROR: {e}")
        return JSONResponse(
            status_code=400, content={"errorMessage": "Can't remove workspace"}
        )


@router.patch("/remove_from_workspace")
async def remove_from_workspace(
    user_id: int, flow_id: int, token=Depends(auth_handler.auth_wrapper)
):
    """Remove flow from selected workspace"""

    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200:
            return user_check
        db.session.query(Flow).filter_by(user_id=user_id).filter_by(id=flow_id).update(
            {"workspace_id": 0, "workspace_name": None}
        )
        db.session.commit()
        db.session.close()
        return JSONResponse(
            status_code=200,
            content={"message": "Flow removed from workspace successfully!"},
        )
    except Exception as e:
        logger.error(f"Failed to removing flow from workspace. ERROR: {e}")
        return JSONResponse(
            status_code=400,
            content={"errorMessage": "Can't remove flow from workspace"},
        )


@router.patch("/rename_workspace")
async def rename_workspace(
    user_id: int,
    workspace_id: int,
    new_name: str,
    token=Depends(auth_handler.auth_wrapper),
):
    """Rename selected workspace"""

    try:
        workspace_names = [
            i[0]
            for i in db.session.query(Workspace.name).filter_by(user_id=user_id).all()
        ]

        if (new_name.rstrip()) in workspace_names:
            return JSONResponse(
                status_code=404, content={"errorMessage": "Name is already exists"}
            )

        db_workspace = db.session.query(Workspace).filter_by(id=workspace_id)
        if db_workspace.first() is None:
            return JSONResponse(
                status_code=404,
                content={"errorMessage": "Can't find flow with given name"},
            )
        else:
            db_workspace.update({"name": new_name})
            [
                db.session.query(Flow)
                .filter_by(id=id[0])
                .update({"workspace_name": new_name})
                for id in db.session.query(Flow.id)
                .filter_by(workspace_id=workspace_id)
                .all()
            ]

            db.session.commit()
            return JSONResponse(
                status_code=200, content={"message": "Name changed successfully!"}
            )
    except Exception as e:
        logger.error(f"Failed to renaming workspace. ERROR: {e}")
        return JSONResponse(
            status_code=400,
            content={"errorMessage": "Can't change the name of workspace"},
        )
