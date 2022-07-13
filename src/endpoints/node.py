import secrets
import json
from fastapi.responses import JSONResponse
from fastapi import APIRouter, status, HTTPException ,encoders , Response, Body,Depends
from typing import List,Dict
from datetime import datetime
from fastapi_sqlalchemy import db

from ..schemas.nodeSchema import NodeSchema,ConnectionSchema,SubNodeSchema,UpdateSubNodeSchema
from ..models.node import Node, NodeType , Connections,CustomFieldTypes, CustomFields, SubNode
from ..models.flow import Flow
from ..models.users import User

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()

router = APIRouter(
    prefix="/node/v1",
    tags=["Node"],
    responses={404: {"description": "Not found"}},
)

async def check_user_token(flow_id:int,token=Depends(auth_handler.auth_wrapper)):
    """
    Check User using token and give the permission
    """
    try:
       get_user_id = db.session.query(User).filter_by(email=token).first()  
       flow_ids = [i[0] for i in db.session.query(Flow.id).filter_by(user_id=get_user_id.id).all()]
       if flow_id in flow_ids:
           return JSONResponse(status_code=200,content={"message":"flow is exists"})
       else:
           return JSONResponse(status_code=404,content={"errorMessage":"flow not exists for this user"})
    except Exception as e:
        print(e,"at:",datetime.now())
        return JSONResponse(status_code=400,content={"errorMessage":"please check input"})

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
    Check node properties based on node type 
    """
    
    prop_dict = {k: v for k, v in prop.items() if k in keys}
    return True, prop_dict

async def check_node_details(node:NodeSchema):
    """
    Check node details based on node type 
    """
    node_type_params = db.session.query(NodeType).filter(NodeType.type == node.type).first()

    if(node_type_params == None):
        return JSONResponse(status_code = 404, content = {"errorMessage": "incorrect type field"}), node.data

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
    Create a node based on schema data and insert into database
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
        count = 1
        if node.type == "conditional_logic":
            for item in prop_dict:
                first_sub_node = SubNode(id=str(new_node.id) + "_" + str(count) + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                second_sub_node = SubNode(id=str(new_node.id) + "_" + str(count + 1) + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(first_sub_node)
                db.session.add(second_sub_node)
        elif node.type == "button":
            for item in prop_dict:
                first_sub_node = SubNode(id=str(new_node.id) + "_" + str(count) + "b", node_id=new_node.id,flow_id=node.flow_id, data={"text":""}, type="chat")
                second_sub_node = SubNode(id=str(new_node.id) + "_" + str(count + 1) + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(first_sub_node)
                db.session.add(second_sub_node)
        else:
            for item in prop_dict:
                new_sub_node = SubNode(id=str(new_node.id) + "_" + str(count) + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(new_sub_node)
                count += 1
        db.session.query(Flow).filter_by(id=node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"}) , node_id
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"})


@router.post('/create_node')
async def create_nodes(node : NodeSchema,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        create_node_response, node_id = await create_node(node)
        if (create_node_response.status_code != 200):
            return create_node_response

        return JSONResponse(status_code=200, content={"message": "success", "ids": node_id})
    except Exception as e:
        print(e,'at create_node')
        return JSONResponse(status_code=404, content={"errorMessage":"Error in creating node"})

@router.delete('/delete_node')
async def delete_node(node_id : str, flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Delete node from database
    """
    try:
        validate_user = await check_user_token(flow_id,token)

        if (validate_user.status_code != 200):
            return validate_user
        node_in_db = db.session.query(Node).filter_by(flow_id = flow_id).filter_by(id = node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})
        node_in_db.delete()
        db.session.query(Connections).filter((Connections.source_node_id == node_id) | (Connections.target_node_id == node_id)).delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Node deleted'})
    except Exception  as e:
        print(e)
        return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"})  

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
            return JSONResponse(status_code=404, content={"errorMessage":"Node not found"})
        
        node_check, node_data = await check_node_details(my_node)
        if(node_check.status_code != 200):
            return node_check
    
        db.session.query(Node).filter(Node.id == node_id).filter_by(flow_id=my_node.flow_id).update({'data' : node_data, 'type' : my_node.type, 'position':my_node.position})
        db.session.query(Flow).filter_by(id=my_node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except:
         return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"}) 

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
            return JSONResponse(status_code=404, content={"errorMessage":"Node or flow id not found"})

        sub_node_list = db.session.query(SubNode.id).filter_by(node_id = sub.node_id).all()
        sub_node_list = [tuple(x) for x in list(sub_node_list)]
        sub_node_list = sorted(sub_node_list)
        
        #logic for the add multiple nodes
        if(sub_node_list != []):
            i = int(list(sub_node_list)[-1][0][-2]) + 1
        else:
            i = 1
        id = str(sub.node_id) + "_" + str(i) +"b"

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

        return JSONResponse(status_code = 200, content = {"message" : "Sub node addedd"})
    except Exception as e:
        print("Error: at add_sub_node.",e)
        return JSONResponse(status_code=404, content={"errorMessage":"Node not present in db"})


@router.put('/update_subnode')
async def update_sub_node(my_sub_node:SubNodeSchema,sub_node_id:str = Body(...),token = Depends(auth_handler.auth_wrapper)):
    """
    Update subnode as per requirements 
    """
    try:
        validate_user = await check_user_token(my_sub_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        node_in_db = db.session.query(SubNode).filter_by(flow_id=my_sub_node.flow_id).filter_by(id=sub_node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Node not found"})

        existing_data = node_in_db.first().data
        for key,value in my_sub_node.data.items():
            existing_data[key] = value
        db.session.query(SubNode).filter_by(flow_id=my_sub_node.flow_id).filter_by(id = sub_node_id).update({'data' : existing_data})
        db.session.commit()

        sub_nodes = db.session.query(SubNode).filter_by(flow_id=my_sub_node.flow_id).filter_by(node_id = my_sub_node.node_id).all()
        node_data = []
        for sub_node in sub_nodes:
            node_data.append(sub_node.data)  
        db.session.query(Node).filter_by(flow_id=my_sub_node.flow_id).filter_by(id = my_sub_node.node_id).update({'data' : existing_data})
        db.session.query(Flow).filter_by(id=my_sub_node.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()  
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except Exception as e:
        print("Error in updating node: ", e)
        return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"})

@router.put('/new_update_subnode')
async def new_update_sub_node(sub:List[UpdateSubNodeSchema],flow_id:int,node_id:int,token = Depends(auth_handler.auth_wrapper)):
    """
    Update sub node/nodes as per recieved data
    """
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        for subnode in sub:
            node_in_db = db.session.query(SubNode).filter_by(flow_id=flow_id).filter_by(id=subnode.sub_node_id)

            if(node_in_db.first() == None):
                return JSONResponse(status_code=404, content={"errorMessage":"Node not found"})

            existing_data = node_in_db.first().data
            for key,value in subnode.data.items():
                existing_data[key] = value
            db.session.query(SubNode).filter_by(flow_id=flow_id).filter_by(id = subnode.sub_node_id).update({'data' : existing_data})
            db.session.commit()

        sub_nodes = db.session.query(SubNode).filter_by(flow_id=flow_id).filter_by(node_id = node_id).all()
        node_data = []
        for sub_node in sub_nodes:
            node_data.append(sub_node.data)  
        db.session.query(Node).filter_by(flow_id=flow_id).filter_by(id = node_id).update({'data' : existing_data})
        db.session.commit()  
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except Exception as e:
        print("Error in updating node: ", e)
        return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"})

@router.delete('/delete_sub_node')
async def delete_sub_node(sub_node_id : str,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        node_in_db = db.session.query(SubNode).filter_by(flow_id = flow_id).filter_by(id = sub_node_id)
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage":"Sub Node not found"})

        node_in_db.delete()
        db.session.query(Connections).filter(Connections.sub_node_id == sub_node_id).delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Sub Node deleted'})
    except:
        return JSONResponse(status_code=404, content={"errorMessage":"Please enter sub_node_id correctly"})  

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
                return JSONResponse(status_code = 404, content = {"errorMessage" : "Node not found"})
        except:
            return JSONResponse(status_code=404, content={"errorMessage":"Please enter node_id correctly"})

        if "" in connection.dict().values( ): 
            Response(status_code = 204)

        connection_name = "c_" + str(connection.source_node_id) + "_" + str(connection.sub_node_id) + "-" + str(connection.target_node_id)
        if(connection.source_node_id == connection.target_node_id):
            return JSONResponse(status_code = 406, content={"errorMessage":"Source and Target node cannot be the same"})
      
        if(db.session.query(Connections).filter_by(flow_id=connection.flow_id).filter_by(source_node_id= connection.source_node_id).filter_by(sub_node_id = connection.sub_node_id).first() is not None):
            db.session.query(Connections).filter(Connections.source_node_id == connection.source_node_id).filter(Connections.sub_node_id == connection.sub_node_id).\
            update({'target_node_id':connection.target_node_id, 'name' : connection_name})
        else:
            new_connection = Connections(sub_node_id = connection.sub_node_id, source_node_id = connection.source_node_id, target_node_id = connection.target_node_id, name = connection_name,flow_id= connection.flow_id)
            db.session.add(new_connection)
        db.session.query(Flow).filter_by(id=connection.flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()

        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print("Error in create connection: ", e)
        return JSONResponse(status_code=404, content={
            "errorMessage": "Cannot create connection. Check if node and flow ids entered correctly"})
         
@router.post('/create_connection')
async def create_connections(connection : ConnectionSchema,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(connection.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        x = await create_connection(connection)
        if(x.status_code != 200):
            return x

        return JSONResponse(status_code = 200, content = {"message" :"success"})
    except Exception as e:
        print("Error in delete connection: ", e)
        return JSONResponse(status_code=404, content={
            "errorMessage": "Cannot create connection. Check if node and flow ids entered correctly"})
    
@router.delete('/delete_connection')
async def delete_connection(connection_id: int,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
 
        connection_in_db = db.session.query(Connections).filter_by(id=connection_id)
        if (connection_in_db.first() == None):
            return JSONResponse(status_code=404, content={"errorMessage": "Connection not found"})
      
        connection_in_db.delete()
        db.session.query(Flow).filter_by(id=flow_id).update({"updated_at": datetime.today().isoformat()})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200, content={'message': 'Connection deleted'})
    except Exception as e:
        print("Error in delete connection: ", e)
        return JSONResponse(status_code=404, content={
            "errorMessage": "Cannot delete connection. Check if node and flow ids entered correctly"})

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
            return JSONResponse(status_code=404, content={"message": "No such subnode exists"})
        create_conn = ConnectionSchema(flow_id=my_node.flow_id, source_node_id=node_id,
                                  sub_node_id=sub_node_id,
                                  target_node_id=my_id)
        await create_connection(create_conn)

        return JSONResponse(status_code=200, content={"message": "Success"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"errorMessage": "Cannot create connections between two nodes"})

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

        return JSONResponse(status_code=200, content={"message": "Success"})
    except Exception as e:
        print("Error in update_connection: ", e)
        return JSONResponse(status_code=404, content={"errorMessage": "Cannot update/add connection"})