import uuid
from fastapi import APIRouter, Depends , encoders,Request
from fastapi.responses import JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi_sqlalchemy import db
from datetime import timezone, datetime
from typing import List,Dict


from ..schemas.flowSchema import FlowSchema,EmbedSchema
from ..models.flow import Flow
from ..models.node import Node,SubNode,CustomFields,Connections
from ..endpoints.node import check_user_token

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/flow/v1",
    tags=["Flow"],
    responses={404: {"description": "Not found"}},
)
templates = Jinja2Templates(directory="/home/brilworks-23/Downloads/Chatbot Project/chatbot_apis/src/endpoints/templates")
async def check_user_id(user_id:str):
    """
    Check User using Id to give  permission
    """
    try:
        if(db.session.query(Flow).filter_by(user_id = user_id).first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"no flows at this id"})
        else:
            return JSONResponse(status_code=200)
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the user id input"})

@router.post('/create_flow')
async def create_flow(flow : FlowSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Create a flow as per user requirements 
    """
    try:
        flow_names =[i[0] for i in db.session.query(Flow.name).filter_by(user_id=flow.user_id).all()]

        if flow.name in flow_names:
            return JSONResponse(status_code=404, content={"errorMessage":"Name is already exists"})
        if(flow.name == None or len(flow.name.strip()) == 0):
            return Response(status_code=204)
        new_flow = Flow(name = flow.name, user_id = flow.user_id, created_at = datetime.today().isoformat(), updated_at = datetime.today().isoformat(),publish_token=None,status = "active", isEnable = True,chats =0, finished=0, workspace_id=0,workspace_name=None)
        db.session.add(new_flow)
        db.session.commit()

        flow_id = db.session.query(Flow.id).filter_by(id = new_flow.id).first()
        node_data = []
        node_data.append({"text": "Welcome","button":"Start"})
        default_node = Node(name = "Welcome", type = "special", data = node_data, position = {"x": 180,"y": 260},flow_id=flow_id[0])
        db.session.add(default_node)
        db.session.commit()
        default_subnode = SubNode(id = str(default_node.id) + "_" + str(1) + "b", node_id = default_node.id, flow_id = default_node.flow_id, data = node_data[0], type = default_node.type)
        db.session.add(default_subnode)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})

@router.get('/get_flow_list')
async def get_flow_list(user_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get the flow list using user id
    """
    try:
        flows = db.session.query(Flow).filter_by(user_id = user_id).filter_by(isEnable = True).all()
        # get the workspace id & list 
        flow_list = []
        for fl in flows:
            flow_list.append({"flow_id":fl.id, "name":fl.name, "updated_at":encoders.jsonable_encoder(fl.updated_at),"created_at":encoders.jsonable_encoder(fl.created_at), "chats":fl.chats,"finished":fl.finished, "publish_token":fl.publish_token,"workspace_id":fl.workspace_id,"workspace_name":fl.workspace_name})
        return JSONResponse(status_code=200, content={"flows" : flow_list})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})

@router.get('/search_flows')
async def search_flows(user_id : int, flow_name:str,token = Depends(auth_handler.auth_wrapper)):
    """
    Serach flow by it's name
    """
    try:
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flows = db.session.query(Flow).filter_by(name = flow_name).all()
        if(len(flows) == 0):
            return JSONResponse(status_code=404, content={"errorMessage":"no flows with this name"})
        else:
            flows_lst = []
            for fl in flows:
                flows_lst.append(fl.id)
            return JSONResponse(status_code=200, content={"message": "success", "flow_ids" : flows_lst})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})


@router.post('/rename_flow')
async def rename_flow(user_id : int, flow_id:int, new_name:str,token = Depends(auth_handler.auth_wrapper)):
    """
    Rename flow
    """
    try:
        flow_names =[i[0] for i in db.session.query(Flow.name).filter_by(user_id=user_id).all()]

        if new_name in flow_names:
            return JSONResponse(status_code=404, content={"errorMessage":"Name is already exists"})
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flows = db.session.query(Flow).filter_by(id = flow_id)
        if(flows.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"no flows with this name"})
        else:
            flows.update({'name' : new_name,"updated_at": datetime.today().isoformat()})
            db.session.commit()
            db.session.close()
            return JSONResponse(status_code=200, content={"message": "success"})
            
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})


@router.delete('/delete_flow_list')
async def delete_flow(user_id : int, flow_list: List[int],token = Depends(auth_handler.auth_wrapper)):
    """
    Delete one flow or multiple flows at a time 
    """
    try:
        for flow_id in flow_list:
            valid_user = await check_user_token(flow_id,token)
            if (valid_user.status_code != 200):
                return valid_user
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200:
            return user_check

        for flow_id in flow_list:
            if (db.session.query(Flow).filter_by(id=flow_id).first() == None):
                return JSONResponse(status_code=404, content={"errorMessage": "no flows with this id"})
            db.session.query(Flow).filter_by(id=flow_id).update({"status": "trashed"})

        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})

    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.post('/duplicate_flow')
async def duplicate_flow(user_id:int, flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Create a copy(duplicate) flow with same characteristics
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        user_check = await check_user_id(user_id)
        if user_check.status_code != 200 :
            return user_check 
        
        flow_data = db.session.query(Flow).filter_by(id = flow_id).first()
        if (flow_data == None):
            return JSONResponse(status_code=404, content={"errorMessage":"please check the id"})   
        my_uuid = uuid.uuid4()
        new_flow = Flow(name = "duplicate of " + flow_data.name, user_id = flow_data.user_id, created_at = datetime.today().isoformat(), updated_at = datetime.today().isoformat(), diagram = flow_data.diagram, publish_token=my_uuid,status = "active", isEnable = True, chats = 0, finished = 0)
        db.session.add(new_flow)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at duplcate flow. Time:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})

@router.get("/get_diagram")
async def get_diagram(flow_id :int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get the diagram which contain all nodes, connections, sub_nodes with data
    """
    try:
        flow_data = db.session.query(Flow).filter_by(id=flow_id).filter_by(status="trashed").first()        
        if (flow_data != None):
            return JSONResponse(status_code=201,content={"errorMessage":"flow is not found"})
        
        all_connections = db.session.query(Connections).filter_by(flow_id=flow_id).all()
        connections_list =[]
        for conn in all_connections:
            get_conn = {"id": str(conn.id), "markerEnd": {"type": "MarkerType.ArrowClosed",},"type": 'buttonedge', "source": str(conn.source_node_id), "sourceHandle": conn.sub_node_id,"target": str(conn.target_node_id), "animated": True, "label": 'edge label', "flow_id":flow_id}
            connections_list.append(get_conn)
        all_custom_fileds = db.session.query(CustomFields).filter_by(flow_id=flow_id).all()
        all_nodes = db.session.query(Node).filter_by(flow_id=flow_id).all()
        sub_nodes = db.session.query(SubNode).filter_by(flow_id=flow_id).all()

        node_list = []
        for node in all_nodes:
            sub_nodes = db.session.query(SubNode).filter_by(node_id = node.id).all()
            sub_node_list = []
            for sub_node in sub_nodes:
                fields = dict(sub_node.data.items()) #get fields of data(text,btn,...)
                my_dict = {"flow_id":sub_node.flow_id, "node_id":sub_node.node_id,"type":sub_node.type,"id":sub_node.id}
                for key,value in fields.items():
                    my_dict[key] = value
                sub_node_list.append(my_dict)
            get_data = {"flow_id" : flow_id,"id": str(node.id), "type": node.type, "position": node.position,
             "data": { "id": node.id,"label": "NEW NODE", "nodeData": sub_node_list}}
            node_list.append(get_data)

        return {"nodes": node_list,"connections": connections_list, "custom_fields": encoders.jsonable_encoder(all_custom_fileds),"sub_nodes:": encoders.jsonable_encoder(sub_nodes)}
    except Exception as e:
        print(e, ": at get diagram")
        return JSONResponse(status_code=400, content={"errorMessage": "Cannot get diagram"})


@router.post('/save_draft')
async def save_draft(flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Save the diagram in database
    """
    try:
        diagram = await get_diagram(flow_id)
        db.session.query(Flow).filter_by(id = flow_id).update({'diagram' : diagram})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"success"})
    except Exception as e:
        print(e, "at:", datetime.now())
        return JSONResponse(status_code=400, content={"errorMessage":"please check the input"})

async def preview(flow_id : int,token = Depends(auth_handler.auth_wrapper)):
    """
    Retun the diagram for the preview (user conversion)
    """
    try:
        get_diagram = db.session.query(Flow).filter_by(id=flow_id).first()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})        
        if (get_diagram == None):
            return JSONResponse(status_code=404, content={"errorMessage":"please publish first"})
        return get_diagram.diagram

    except Exception as e:
        print("Error at send: ", e)
        return JSONResponse(status_code=404, content={"errorMessage": "Send Chat data Not Found"})

@router.post('/{my_token}/preview')
async def tokenize_preview(my_token:str,token = Depends(auth_handler.auth_wrapper)):
    """
    Retun the diagram for the preview using valid token(user conversion)
    """
    try:
        flow_id =  db.session.query(Flow.id).filter_by(publish_token = my_token).first()[0]

        if(my_token in db.session.query(Flow.publish_token).filter_by(publish_token = my_token).first()[0]):
            return await preview(flow_id, token = Depends(auth_handler.auth_wrapper))
        else:
            return JSONResponse(status_code = 404, content={"errorMessage":"Cannot open preview. Token not identified"})
    except Exception as e:
        print("Error: in  my_token/preview", e)
        return JSONResponse(status_code = 404, content={"errorMessage":"Cannot open preview"})
    
@router.post('/publish')
async def publish(flow_id: int,diagram : Dict,token = Depends(auth_handler.auth_wrapper)):
    """
    Save latest diagram(nodes,connections,sub_nodes) with token in database
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        save_draft_status = await save_draft(flow_id)
        if (save_draft_status.status_code != 200):
            return save_draft_status

        my_uuid = uuid.uuid4()
        if (diagram ==None):
            return JSONResponse(status_code=404, content={"errorMessage": "diagram field is empty!!"})

        db.session.query(Flow).filter_by(id = flow_id).update({'updated_at' : datetime.today().isoformat(), 'diagram' : diagram,'publish_token': my_uuid})
        db.session.commit()
        db.session.close()

        if (token == None):
            return JSONResponse(status_code=404, content={"errorMessage": "Cannot publish. Check flow_id entered"})

        return {"message": "success", "token": my_uuid}
    except Exception as e:
        print("Error in publish: ", e)
        return JSONResponse(status_code=400, content={"errorMessage": "Cannot publish"})

@router.post("/disable_flow")
async def flow_disabled(flow_id: int,token = Depends(auth_handler.auth_wrapper)):
    """
    Disable flow means it can't be publish 
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"isEnable": False})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200, content={"message": "flow disabled"})
    except Exception as e:
        print("Error at disable_flow: ", e)
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.patch('/archive_flow')
async def archive_flow(flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Move into trash folder
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"isEnable": False, "status": "trashed"})
        db.session.query(Flow).filter_by(id = flow_id).update({"workspace_id":0,'workspace_name': None})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200,content={"message" : "flow moved into trash folder"})
    except Exception as e:
        print("Error at archive flow: ", e)
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.get('/get_trashed_flows')
async def get_trashed_flows(user_id: int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get the list of flows which in trash folder
    """
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
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.delete('/trash/delete_forever')
async def delete_flow(flow_id: int,token = Depends(auth_handler.auth_wrapper)):
    """
    Delete permanently flow
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).filter_by(isEnable=False).filter_by(status="trashed").delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print("Error at delete_forever: ", e)
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.post('/trash/restore_flow')
async def restore_flow(flow_id: int,token = Depends(auth_handler.auth_wrapper)):
    """
    Restore any flow and use it 
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        db.session.query(Flow).filter_by(id=flow_id).update(
            {"status": "active", "isEnable": True, "updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200, content={"message": "success"})
    except Exception as e:
        print("Error at restore: ", e)
        return JSONResponse(status_code=400, content={"errorMessage": "please check the input"})


@router.get("/flow_detail")
async def get_flow_detail(flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Get flow details name and publish_token
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        db_name =  db.session.query(Flow).filter_by(id=flow_id).first()
        token = db.session.query(Flow.publish_token).first()[0]
        return JSONResponse(status_code=200,content={"name":db_name.name,"publish_token":token})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"something is wrong"})

@router.get("/get_embed_code")
async def get_embed_code(request: Request,schema:EmbedSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Get the embed Script to integrate bot into webpage
    """
    try:
        valid_user = await check_user_token(schema.flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        if schema.type == 'livechat': 
            return templates.TemplateResponse("livechat.html", {"request": request, "config_url":schema.config_url})
        elif schema.type == 'fullpage': 
            return templates.TemplateResponse("fullpage.html", {"request": request, "config_url":schema.config_url})
        elif schema.type == 'embed': 
            return templates.TemplateResponse("embed.html", {"request": request, "config_url":schema.config_url})
        elif schema.type == 'popup': 
            return templates.TemplateResponse("popup.html", {"request": request, "config_url":schema.config_url})
        else: 
            return JSONResponse(status_code=404,content={"errorMessage":"Select correct Type"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Can't access embed code"})
