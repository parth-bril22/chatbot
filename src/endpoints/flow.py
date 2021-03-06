import uuid
import boto3
import collections
from fastapi import APIRouter, Depends , encoders, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi_sqlalchemy import db
from datetime import datetime
from typing import List,Dict


from ..dependencies.env import AWS_ACCESS_KEY,AWS_ACCESS_SECRET_KEY,BUCKET_NAME

from ..schemas.flowSchema import FlowSchema,ChatSchema
from ..models.flow import Flow,Chat,EmbedScript
from ..models.node import Node,SubNode,CustomFields,Connections
from ..endpoints.node import check_user_token

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/flow/v1",
    tags=["Flow"],
    responses={404: {"description": "Not found"}},
)

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
        flow_names =[i[0] for i in db.session.query(Flow.name).filter_by(user_id=flow.user_id).filter_by(status = 'active').all()]

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
        sorted_list = sorted(flow_list, key=lambda flow_list: flow_list['flow_id'],reverse = True)
        return JSONResponse(status_code=200, content={"flows" : sorted_list})
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
        flow_names =[i[0] for i in db.session.query(Flow.name).filter_by(user_id=user_id).filter_by(status = 'active').all()]

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
                my_dict = {"flow_id":sub_node.flow_id, "node_id":sub_node.node_id,"type":sub_node.type,"id":sub_node.id, "data":fields}
                # for key,value in fields.items():
                #     my_dict[key] = value
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
async def tokenize_preview(my_token:str):
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
    Save latest diagram(nodes,connections,sub_nodes) with token in database and allow to publish 
    """
    try:
        valid_user = await check_user_token(flow_id,token)
        if (valid_user.status_code != 200):
            return valid_user
        save_draft_status = await save_draft(flow_id)
        if (save_draft_status.status_code != 200):
            return save_draft_status
        
        db_token =  db.session.query(Flow.publish_token).filter_by(id = flow_id).first()[0]
        if db_token != None:
            publish_token = db_token
        else:
            publish_token = uuid.uuid4()

        if (diagram ==None):
            return JSONResponse(status_code=404, content={"errorMessage": "diagram field is empty!!"})

        db.session.query(Flow).filter_by(id = flow_id).update({'updated_at' : datetime.today().isoformat(), 'diagram' : diagram,'publish_token': publish_token})
        db.session.commit()
        db.session.close()

        if (token == None):
            return JSONResponse(status_code=404, content={"errorMessage": "Cannot publish. Check flow_id entered"})

        return {"message": "success", "token": publish_token}
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


@router.post("/save_chat_history")
async def save_chat_history(chats:ChatSchema):
    """
    Save the chat history of every user
    """
    try:
        get_visitor = db.session.query(Chat).filter_by(visitor_ip=chats.visitor_ip).filter_by(flow_id=chats.flow_id).first()

        if (get_visitor != None):
            db.session.query(Chat).filter_by(visitor_ip=chats.visitor_ip).update({"chat":chats.chat})
        else:
            new_chat = Chat(flow_id = chats.flow_id, visited_at = datetime.today().isoformat(), updated_at = datetime.today().isoformat(),chat = chats.chat,visitor_ip=chats.visitor_ip)
            db.session.add(new_chat)
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200,content={"message":"Success"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Error in save chathistory"})

@router.get("/get_chat_history")
async def get_chat_history(ip:str,flow_id:int):
    """
    Get the chat history of every user
    """
    try:
        chat_history = db.session.query(Chat).filter_by(visitor_ip=ip).filter_by(flow_id=flow_id).first()
        if (chat_history == None):
            return JSONResponse(status_code=400,content={"errorMessage":"Can't find ip address"})
        chat_data = {"chat":chat_history.chat,"flow_id":chat_history.flow_id}
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200,content=chat_data)
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Can't find chat history"})

@router.post("/upload")
async def upload_file_to_s3(flow_id:int,file: UploadFile):    
    """
    Upload the html file into s3 bucket
    """
    try:
        
        s3 = boto3.resource("s3",aws_access_key_id =AWS_ACCESS_KEY,aws_secret_access_key=AWS_ACCESS_SECRET_KEY)
        bucket = s3.Bucket(BUCKET_NAME)
        bucket.upload_fileobj(file.file,'embedfile/'+str(flow_id)+'/'+(file.filename),ExtraArgs={'ContentType':'text/html'})

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com/embedfile/{flow_id}/{file.filename}"

        db_file=EmbedScript(file_name = file.filename, created_at = datetime.today().isoformat(),file_url = s3_file_url)
        db.session.add(db_file)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200,content={"message":"Success"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Error at uploading file"})

@router.post("/upload_user")
async def upload_file_from_user(flow_id:int,file: UploadFile):    
    """
    Upload the html file into s3 bucket
    """
    try:
        
        s3 = boto3.resource("s3",aws_access_key_id =AWS_ACCESS_KEY,aws_secret_access_key=AWS_ACCESS_SECRET_KEY)
        bucket = s3.Bucket(BUCKET_NAME)
        bucket.upload_fileobj(file.file,'visitorfiles/'+str(flow_id)+'/'+(file.filename),ExtraArgs={'ContentType':'text/html'})

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com/visitorfiles/{flow_id}/{file.filename}"
        return JSONResponse(status_code=200,content={"message":"Success"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Error at uploading file"})

@router.get("/flow_analysis")
async def get_flow_analysis_data(flow_id:int):
    try:

        diagram = await get_diagram(flow_id)
        connections = diagram['connections']
        total_visits = len(db.session.query(Chat.flow_id).filter_by(flow_id=flow_id).all())
        chat_data = db.session.query(Chat.chat).filter_by(flow_id=flow_id).all()
        if total_visits == 0:
            return JSONResponse(status_code=404,content={"errorMessage":"There is no visitors!"})
        subnode_list=[]
        input_types = ['url','file',"text",'number','phone','email','date']
        pop_list = []
        for i in range(len(chat_data)):
            if chat_data[i][0][-1]['type'] in input_types:
                pop_list.append(chat_data[i][0][-1]['id'])
            else:
                pop_list
            id_list =[]
            for i in chat_data[i][0]:
                if i['type'] == 'button':
                    id_list.append(i['id'])
                elif 'from' in i:   
                    pass
                elif i['id'] in pop_list:
                    pass
                else:
                    id_list.append(i['id'])
            subnode_list.extend(list(set(id_list)))

        subnode_set = list(set(subnode_list))
        subnode_frequency = dict(collections.Counter(subnode_list))

        for conn in connections:
            if conn['sourceHandle'] in subnode_set:
                n=subnode_frequency[conn['sourceHandle']]
                conn['data'] = {'n':n,'percentage':str(round(n/total_visits*100))+'%'}
            else:
                conn['data'] = {'n':0,'percentage':'0'+'%'}

        return {"nodes": diagram['nodes'],"connections": connections}
    except Exception as e:
        print(e)
        return JSONResponse(status_code=400,content={"errorMessage":"Error at get that data"})

@router.post("/upload_from_user")
async def upload_to_s3_from_user(file:UploadFile,node_id:int,flow_id:int):
    try:
        s3 = boto3.resource("s3",aws_access_key_id =AWS_ACCESS_KEY,aws_secret_access_key=AWS_ACCESS_SECRET_KEY)
        bucket = s3.Bucket(BUCKET_NAME)
        
        if(db.session.query(Node).filter_by(id = node_id).filter_by(flow_id=flow_id).first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Node not found"})
    
        if file.content_type == 'image/png':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'image/png'})
        elif file.content_type == 'image/gif':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'image/gif'})  
        elif file.content_type in 'video/mp4':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'video/mp4'})  
        elif file.content_type == 'text/html':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'text/html'})
        elif file.content_type == 'text/plain':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'text/plain'})
        elif file.content_type == 'application/msword':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'application/msword'})
        elif file.content_type == 'application/pdf':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'application/pdf'})
        elif file.content_type == 'audio/mpeg':
            bucket.upload_fileobj(file.file,'userfiles/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':'audio/mpeg'})


        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com/userfiles/{flow_id}/{node_id}/{file.filename}"
        return JSONResponse(status_code=200,content={"message":"Successfully Uploaded","url":s3_file_url})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"errorMessage":"Error at uploading"})
