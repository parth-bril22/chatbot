import boto3
import secrets
import json
from fastapi.responses import JSONResponse
from fastapi import APIRouter, status, HTTPException ,encoders , Response,Depends,UploadFile
from typing import List,Dict
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.nodeSchema import NodeSchema,ConnectionSchema,SubNodeSchema,UpdateSubNodeSchema
from ..models.node import Node, NodeType,Connections,SubNode
from ..models.flow import Flow
from ..models.users import User

from ..dependencies.config import AWS_ACCESS_KEY,AWS_ACCESS_SECRET_KEY,BUCKET_NAME
from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/api/node/v1",
    tags=["Node"],
    responses={404: {"description": "Not found"}},
)

async def upload_to_s3(file,node_id,flow_id):
    try:
        s3 = boto3.resource("s3",aws_access_key_id =AWS_ACCESS_KEY,aws_secret_access_key=AWS_ACCESS_SECRET_KEY)
        bucket = s3.Bucket(BUCKET_NAME)
        
        CONTENT_TYPES = ['image/png','image/jpeg','image/jpg','image/gif','video/mp4','text/html','image/svg+xml','text/plain','application/msword','application/pdf',
        'audio/mpeg','text/csv','application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type in CONTENT_TYPES:
            bucket.upload_fileobj(file.file,'mediafile/'+str(flow_id)+'/'+str(node_id)+'/'+(file.filename),ExtraArgs={'ContentType':file.content_type})

        s3_file_url = f"https://{BUCKET_NAME}.s3.ap-south-1.amazonaws.com/mediafile/{flow_id}/{node_id}/{file.filename}"
        db_subnode_data = db.session.query(SubNode).filter_by(flow_id=flow_id).filter_by(node_id=node_id).first()
        db_subnode_data.data.update({'name':file.filename})
        db_subnode_data.data.update({'source': s3_file_url})
        db_subnode_data.data.update({'content_type':file.content_type})
    
        db.session.query(SubNode).filter_by(flow_id=db_subnode_data.flow_id).filter_by(id = db_subnode_data.id).update({'data' : db_subnode_data.data})
        db.session.commit()
        sub_nodes = db.session.query(SubNode).filter_by(flow_id=db_subnode_data.flow_id).filter_by(node_id = db_subnode_data.node_id).all()
        node_data = []
        for sub_node in sub_nodes:
            node_data.append(sub_node.data)  

        db.session.query(Node).filter_by(flow_id=sub_node.flow_id).filter_by(id = sub_node.node_id).update({'data' : node_data})
        db.session.query(Flow).filter_by(id=sub_node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()  
        db.session.close()
        return JSONResponse(status_code=200,content={"message":"Successfully Uploaded"})
    except Exception as e:
        print(e,"at upload to s3. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't upload"})

async def check_user_token(flow_id:int,token=Depends(auth_handler.auth_wrapper)):
    """
    Check User using token and give the permission
    """
    try:
       get_user_id = db.session.query(User).filter_by(email=token).first()  
       flow_ids = [i[0] for i in db.session.query(Flow.id).filter_by(user_id=get_user_id.id).all()]
       if flow_id in flow_ids:
           return JSONResponse(status_code=200,content={"message":"Flow is exists"})
       else:
           return JSONResponse(status_code=404,content={"errorMessage":"Can't find user"})
    except Exception as e:
        print(e,"at check user. Time:", datetime.now())
        return JSONResponse(status_code=400,content={"errorMessage":"Can't authorized"})

async def check_conditional_logic(prop_value_json : json):
    """
    Input format:
    "{\"||\" : {\"args\":[{\"==\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}, {\"<\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}]}}"

    Check if json is empty or not
    then check at five levels:
    via if /else: 1)||, 2)args, 3) "==", 4)arg1,
    via try/except: 5) 1

    """
    if(len(prop_value_json.keys( )) == 0 ):
        raise HTTPException(status_code = status.HTTP_204_NO_CONTENT, )
    else:
        for ele in list(prop_value_json.keys()): 
                if ele not in ["||", "&&", "!"]:
                    Response(status_code = 204)
                else:
                    if "args" in prop_value_json[ele]:
                        for all_symbols in prop_value_json[ele]["args"]:
                            symbol = list(all_symbols.keys())[0]

                            if symbol not in ["==", "<", ">"] or len(list(all_symbols.keys())) != 1:
                                Response(status_code = 204)
                            else:
                                all_args = (list((all_symbols[symbol]).keys()))
                                for arg in all_args:
                                    if arg not in ["arg1", "arg2"]:
                                        Response(status_code = 204)
                                    else:
                                        try:
                                            value = json.loads(all_symbols[symbol][arg])
                                            value + 1
                                        except:
                                            Response(status_code = 204)
                    else:
                        Response(status_code = 204)
    return True

async def check_property_dict(prop : Dict, keys : List):
    """
    Validate node properties based on type 
    """
    
    prop_dict = {k: v for k, v in prop.items() if k in keys}
    return True, prop_dict

async def check_node_details(node:NodeSchema):
    """
    Validate node details(data) based on type 
    """
    node_type_params = db.session.query(NodeType).filter(NodeType.type == node.type).first()

    if(node_type_params == None):
        return JSONResponse(status_code = 404, content = {"errorMessage": "Can't find type"}), node.data

    props = []
    for property in node.data['nodeData']:
        bool_val, prop_dict = await check_property_dict(property,list(node_type_params.params.keys()))
        if(bool_val == False):
            return prop_dict,{}
        else:
            props.append(prop_dict)
    return JSONResponse(status_code=200), props

async def create_node(node:NodeSchema):
    """
    Create a node based on types
    """
    try:
        node_check, node_data = await check_node_details(node)
        if(node_check.status_code != 200):
            return node_check

        prop_dict = node_data
        node_name = secrets.token_hex(4)

        new_node = Node(name = node_name, type = node.type, data = prop_dict , position = node.position, flow_id = node.flow_id)
        db.session.add(new_node)
        db.session.commit()
        node_id = new_node.id
        count = '01'
        if node.type == "conditional_logic":
            for item in prop_dict:
                first_sub_node = SubNode(id=str(new_node.id) + "_" + count + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                second_sub_node = SubNode(id=str(new_node.id) + "_" + '02' + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(first_sub_node)
                db.session.add(second_sub_node)
        elif node.type == "button":
            for item in prop_dict:
                first_sub_node = SubNode(id=str(new_node.id) + "_" + count + "b", node_id=new_node.id,flow_id=node.flow_id, data={"text":""}, type="chat")
                second_sub_node = SubNode(id=str(new_node.id) + "_" + '02' + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(first_sub_node)
                db.session.add(second_sub_node)
        else:
            for item in prop_dict:
                new_sub_node = SubNode(id=str(new_node.id) + "_" + count + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(new_sub_node)
                # count += 1
        db.session.query(Flow).filter_by(id=node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"Node created successfully!"}) , node_id
    except Exception as e:
        print(e,"at creating node. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't create a node"})


@router.post('/create_node')
async def create_nodes(node : NodeSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Create a node based on types
    """
    try:
        validate_user = await check_user_token(node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        create_node_response, node_id = await create_node(node)
        if (create_node_response.status_code != 200):
            return create_node_response

        return JSONResponse(status_code=200, content={"message": "Node created successfully!", "ids": node_id})
    except Exception as e:
        print(e,"at creating node. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't create a node"})

@router.post('/upload_file')
async def upload_files_to_s3(file:UploadFile,node_id:int,flow_id:int):
    """
    Upload file for media & ohter file for file and media node
    """
    try:
        upload_file = await upload_to_s3(file,node_id,flow_id)

        if (upload_file.status_code != 200):
            return JSONResponse(status_code=400,content={"message":"File not uploaded"})

        return JSONResponse(status_code=200, content={"message": "File Uploaded Successfully!","filename":file.filename})
    except Exception as e:
        print(e,"at upload file. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't upload file"})

@router.delete('/delete_node')
async def delete_node(node_id : str, flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Delete node 
    """
    try:
        validate_user = await check_user_token(flow_id,token)

        if (validate_user.status_code != 200):
            return validate_user
        node_in_db = db.session.query(Node).filter_by(flow_id = flow_id).filter_by(id = node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Can't find node"})
        node_in_db.delete()
        db.session.query(Connections).filter((Connections.source_node_id == node_id) | (Connections.target_node_id == node_id)).delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Node deleted successfully!'})
    except Exception  as e:
        print(e,"at delete node. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't delete node"})  

@router.put('/update_node')
async def update_node(node_id:str,my_node:NodeSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Update node details as per user requirements
    """
    try:
        validate_user = await check_user_token(my_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        if(db.session.query(Node).filter_by(id = node_id).filter_by(flow_id=my_node.flow_id).first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Can't find node"})
        
        node_check, node_data = await check_node_details(my_node)
        if(node_check.status_code != 200):
            return node_check
    
        db.session.query(Node).filter(Node.id == node_id).filter_by(flow_id=my_node.flow_id).update({'data' : node_data, 'type' : my_node.type, 'position':my_node.position})
        db.session.query(Flow).filter_by(id=my_node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"Node successfully updated!"})
    except Exception as e:
        print(e,"at updating node. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't update the node"}) 

@router.post("/add_sub_node")
async def add_sub_node(sub:SubNodeSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Add sub nodes as per requiements (it can be multiple)
    """
    try:
        validate_user = await check_user_token(sub.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
            
        if(db.session.query(Node).filter_by(id = sub.node_id).filter_by(flow_id=sub.flow_id).first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Can't find node"})

        sub_node_list = db.session.query(SubNode.id).filter_by(node_id = sub.node_id).all()
        sub_node_list = [tuple(x) for x in list(sub_node_list)]
        sub_node_list = sorted(sub_node_list)
        
        #logic for the add multiple nodes
        if(sub_node_list != []):
            sort_new_list = sorted([i[0].split('_')[1] for i in sub_node_list])
            i = int(sort_new_list[-1][:2]) + 1 
        else:
            i = '01'
        id = str(sub.node_id) + "_" + i +"b"

        relevant_items = dict()
        current_node = db.session.query(Node).filter_by(id = sub.node_id).first()
        relevant_items = dict()
        for k,v in sub.data.items():
            if(k and v != None):
                relevant_items[k] = v
        
        new_sub_node = SubNode(id = id, node_id = sub.node_id, data = encoders.jsonable_encoder(relevant_items),flow_id = sub.flow_id, type = sub.type)
        db.session.add(new_sub_node)

        if current_node.data == None: 
            current_node.data = []
        current_node.data = list(current_node.data)
        current_node.data.append(relevant_items)
        db.session.merge(current_node)
        db.session.query(Flow).filter_by(id=sub.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message" : "Sub node addedd successfully!"})
    except Exception as e:
        print(e,"at add subnode. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't add sub node"})

async def update_subnode(sub_node:UpdateSubNodeSchema,token):
    try :
        validate_user = await check_user_token(sub_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        node_in_db = db.session.query(SubNode).filter_by(flow_id=sub_node.flow_id).filter_by(id=sub_node.id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Can't find node"})

        existing_data = node_in_db.first().data
        for key,value in sub_node.data.items():
            existing_data[key] = value
        db.session.query(SubNode).filter_by(flow_id=sub_node.flow_id).filter_by(id = sub_node.id).update({'data' : existing_data})
        db.session.commit()

        sub_nodes = db.session.query(SubNode).filter_by(flow_id=sub_node.flow_id).filter_by(node_id = sub_node.node_id).all()
        node_data = []
        for sub_node in sub_nodes:
            node_data.append(sub_node.data)  

        db.session.query(Node).filter_by(flow_id=sub_node.flow_id).filter_by(id = sub_node.node_id).update({'data' : node_data})
        db.session.query(Flow).filter_by(id=sub_node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()  
        db.session.close()
        return JSONResponse(status_code=200, content={"message":"Subnode updated"})
    except Exception as e:
        print(e,"at update subnode. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't update subnode"})

@router.put('/update_subnode')
async def update_sub_node(sub_nodes:List[UpdateSubNodeSchema],token = Depends(auth_handler.auth_wrapper)):
    """
    Update Multiple subnodes or a subnode 
    """
    try:
        for subnode in sub_nodes:
            await update_subnode(subnode,token)
        return JSONResponse(status_code = 200, content = {"message":"Subnode updated successfully!"})
    except Exception as e:
        print(e,"at update subnode. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't update subnode"})

@router.delete('/delete_sub_node')
async def delete_sub_node(sub_node_id : str,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        node_in_db = db.session.query(SubNode).filter_by(flow_id = flow_id).filter_by(id = sub_node_id)
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Can't find subnode"})

        node_in_db.delete()
        db.session.query(Connections).filter(Connections.sub_node_id == sub_node_id).delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Sub Node deleted'})
    except Exception as e:
        print(e,"at delete subnode. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage":"Can't delete subnode"})  

# @lru_cache
async def create_connection(connection : ConnectionSchema):
    """
    Create a connection(edge) between nodes
    """
    try:
        if connection.sub_node_id == "" : connection.sub_node_id = "b"
        try:
            source_node_exists = db.session.query(Node).filter((Node.id == connection.source_node_id)).first()
            target_node_exists = db.session.query(Node).filter((Node.id == connection.target_node_id)).first()

            if(source_node_exists == None or target_node_exists == None):
                return JSONResponse(status_code = 404, content = {"errorMessage" : "Can't find node"})
        except:
            return JSONResponse(status_code=404, content={"errorMessage":"Can't create  connection"})

        if "" in connection.dict().values( ): 
            Response(status_code = 204)

        connection_name = "c_" + str(connection.source_node_id) + "_" + str(connection.sub_node_id) + "-" + str(connection.target_node_id)
        if(connection.source_node_id == connection.target_node_id):
            return JSONResponse(status_code = 406, content={"errorMessage":"Source and Target node can't be the same"})
      
        if(db.session.query(Connections).filter_by(flow_id=connection.flow_id).filter_by(source_node_id= connection.source_node_id).filter_by(sub_node_id = connection.sub_node_id).first() is not None):
            db.session.query(Connections).filter(Connections.source_node_id == connection.source_node_id).filter(Connections.sub_node_id == connection.sub_node_id).\
            update({'target_node_id':connection.target_node_id, 'name' : connection_name})
        else:
            new_connection = Connections(sub_node_id = connection.sub_node_id, source_node_id = connection.source_node_id, target_node_id = connection.target_node_id, name = connection_name,flow_id= connection.flow_id)
            db.session.add(new_connection)
        db.session.query(Flow).filter_by(id=connection.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        return JSONResponse(status_code = 200, content = {"message": "Connection created succssfully!"})
    except Exception as e:
        print(e,"at creating connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={
            "errorMessage": "Can't create connection."})
         
@router.post('/create_connection')
async def create_connections(connection : ConnectionSchema,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(connection.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        x = await create_connection(connection)
        if(x.status_code != 200):
            return x

        return JSONResponse(status_code = 200, content = {"message" :"Connection created succssfully!"})
    except Exception as e:
        print(e,"at creating connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={
            "errorMessage": "Can't create connection."})
    
@router.delete('/delete_connection')
async def delete_connection(connection_id: int,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
 
        connection_in_db = db.session.query(Connections).filter_by(id=connection_id)
        if (connection_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage": "Can't find connections"})
      
        connection_in_db.delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200, content={'message': 'Connection deleted'})
    except Exception as e:
        print(e,"at deleting connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={
            "errorMessage": "Can't delete connection."})

@router.post("/create_node_with_conn")
async def create_node_with_conn(my_node:NodeSchema,node_id:int, sub_node_id:str,token = Depends(auth_handler.auth_wrapper)):
    """
    Create a connection with creating node, both  created at a time 
    """
    try:
        validate_user = await check_user_token(my_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        create_node_response, my_id = await create_node(node=my_node)
        if (create_node_response.status_code != 200):
            return create_node_response
        sub_node = db.session.query(SubNode.id).filter_by(node_id=node_id).filter_by(id=sub_node_id).first()
        if (sub_node == None):
            return JSONResponse(status_code=404, content={"message": "Can't find subnode"})
        create_conn = ConnectionSchema(flow_id=my_node.flow_id, source_node_id=node_id,
                                  sub_node_id=sub_node_id,
                                  target_node_id=my_id)
        await create_connection(create_conn)

        return JSONResponse(status_code=200, content={"message": "Created connection from node"})
    except Exception as e:
        print(e,"at creating connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage": "Can't create connection"})

@router.post('/add_connection')
async def add_connection(my_node: NodeSchema, connection: ConnectionSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Add connections for node which has already connections 
    """
    try:
        validate_user = await check_user_token(my_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        status, new_node_id = await create_node(node=my_node)
        if (status.status_code != 200):
            return status

        first_connection = ConnectionSchema(flow_id=connection.flow_id, source_node_id=connection.source_node_id,
                                  sub_node_id=connection.sub_node_id, target_node_id=new_node_id)
        await create_connection(first_connection)

        sub_node_id = db.session.query(SubNode.id).filter_by(node_id=new_node_id).filter_by(
            flow_id=connection.flow_id).first()
        sub_node_id = sub_node_id[0]

        second_connection = ConnectionSchema(flow_id=connection.flow_id, source_node_id=new_node_id, sub_node_id=sub_node_id,
                                  target_node_id=connection.target_node_id)
        await create_connection(second_connection)

        return JSONResponse(status_code=200, content={"message": "Added connection successfully!"})
    except Exception as e:
        print(e,"at adding connection. Time:", datetime.now())
        return JSONResponse(status_code=404, content={"errorMessage": "Can't add connection"})