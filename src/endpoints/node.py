import secrets
import json
from fastapi.responses import JSONResponse
from fastapi import APIRouter, status, HTTPException ,encoders , Response, Body,Depends
from typing import List,Dict
from datetime import datetime,timezone
from fastapi_sqlalchemy import db

from ..schemas.nodeSchema import NodeSchema,ConnectionSchema,SubNodeSchema
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
           return JSONResponse(status_code=404,content={"message":"flow not exists for this user"})
    except Exception as e:
        print(e,"at:",datetime.now())
        return JSONResponse(status_code=400,content={"message":"please check input"})

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
        return JSONResponse(status_code = 404, content = {"message": "incorrect type field"}), node.data

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
        else:
            for item in prop_dict:
                new_sub_node = SubNode(id=str(new_node.id) + "_" + str(count) + "b", node_id=new_node.id,flow_id=node.flow_id, data=item, type=node.type)
                db.session.add(new_sub_node)
                count += 1
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"}) , node_id
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})


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
        return JSONResponse(status_code=404, content={"message":"Error in creating node"})

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
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Node deleted'})
    except Exception  as e:
        print(e)
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})  

@router.put('/update_node')
async def update_node(node_id:str,my_node:NodeSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Update node details as per user requirements
    """
    try:
        validate_user = await check_user_token(my_node.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        node_in_db = db.session.query(Node).filter_by(id = node_id).filter_by(flow_id=my_node.flow_id)
       
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})
        
        node_check, node_data = await check_node_details(my_node)
        if(node_check.status_code != 200):
            return node_check
    
        db.session.query(Node).filter(Node.id == node_id).filter_by(flow_id=my_node.flow_id).update({'data' : node_data, 'type' : my_node.type, 'position':my_node.position})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except:
         return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"}) 

@router.post("/add_sub_node")
async def add_sub_node(sub:SubNodeSchema,token = Depends(auth_handler.auth_wrapper)):
    """
    Add sub nodes as per requiements (it can be multiple)
    """
    try:
        validate_user = await check_user_token(sub.flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
        node_in_db = db.session.query(Node).filter_by(id = sub.node_id).filter_by(flow_id=sub.flow_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node or flow id not found"})

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
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message" : "Sub node addedd"})
    except Exception as e:
        print("Error: at add_sub_node.",e)
        return JSONResponse(status_code=404, content={"message":"Node not present in db"})


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
            return JSONResponse(status_code=404, content={"message":"Node not found"})

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
        db.session.commit()  
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except Exception as e:
        print("Error in updating node: ", e)
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})

@router.delete('/delete_sub_node')
async def delete_sub_node(sub_node_id : str,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user

        node_in_db = db.session.query(SubNode).filter_by(flow_id = flow_id).filter_by(id = sub_node_id)
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Sub Node not found"})

        node_in_db.delete()
        db.session.query(Connections).filter(Connections.sub_node_id == sub_node_id).delete()
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {'message': 'Sub Node deleted'})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter sub_node_id correctly"})  

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
                return JSONResponse(status_code = 404, content = {"message" : "Node not found"})
        except:
            return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})

        if "" in connection.dict().values( ): 
            Response(status_code = 204)

        connection_name = "c_" + str(connection.source_node_id) + "_" + str(connection.sub_node_id) + "-" + str(connection.target_node_id)
        if(connection.source_node_id == connection.target_node_id):
            return JSONResponse(status_code = 406, content={"message":"Source and Target node cannot be the same"})
      
        if(db.session.query(Connections).filter_by(flow_id=connection.flow_id).filter_by(source_node_id= connection.source_node_id).filter_by(sub_node_id = connection.sub_node_id).first() is not None):
            db.session.query(Connections).filter(Connections.source_node_id == connection.source_node_id).filter(Connections.sub_node_id == connection.sub_node_id).\
            update({'target_node_id':connection.target_node_id, 'name' : connection_name})
        else:
            new_connection = Connections(sub_node_id = connection.sub_node_id, source_node_id = connection.source_node_id, target_node_id = connection.target_node_id, name = connection_name,flow_id= connection.flow_id)
            db.session.add(new_connection)
        db.session.commit()

        return JSONResponse(status_code = 200, content = {"message": "success"})
    except Exception as e:
        print("Error in create connection: ", e)
        return JSONResponse(status_code=404, content={
            "message": "Cannot create connection. Check if node and flow ids entered correctly"})
         
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
            "message": "Cannot create connection. Check if node and flow ids entered correctly"})
    
@router.delete('/delete_connection')
async def delete_connection(connection_id: int,flow_id:int,token = Depends(auth_handler.auth_wrapper)):
    try:
        validate_user = await check_user_token(flow_id,token)
        if (validate_user.status_code != 200):
            return validate_user
 
        connection_in_db = db.session.query(Connections).filter_by(id=connection_id)
        if (connection_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message": "Connection not found"})
      
        connection_in_db.delete()
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200, content={'message': 'Connection deleted'})
    except Exception as e:
        print("Error in delete connection: ", e)
        return JSONResponse(status_code=404, content={
            "message": "Cannot delete connection. Check if node and flow ids entered correctly"})

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
        create_connection = ConnectionSchema(flow_id=my_node.flow_id, source_node_id=node_id,
                                  sub_node_id=sub_node_id,
                                  target_node_id=my_id)
        await create_connection(create_connection)

        return JSONResponse(status_code=200, content={"message": "Success"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"message": "Cannot create connections between two nodes"})

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
        return JSONResponse(status_code=404, content={"message": "Cannot update/add connection"})



# async def create_custom_field(cus : CustomFieldSchema):

#     prop = db.session.query(CustomFieldTypes).filter(CustomFieldTypes.type == cus.type).first()
    
#     if(prop == None):
#         raise HTTPException(status_code = status.HTTP_204_NO_CONTENT)
#     if "" in cus.dict().values( ):
#         raise HTTPException(status_code = status.HTTP_204_NO_CONTENT)

#     try:
#         ip_type = type(literal_eval(cus.value))
#         if(cus.type == "number"):
#             my_type = str(ip_type).split(" ")[-1][:-1].strip("\'")
#             if my_type != "int" and my_type != "float":
#                 return JSONResponse(status_code = 404, content={"message": "please check your number"})
#         else:
#             raise ValueError
#     except (ValueError, SyntaxError):
#         if cus.type == "text":
#             print("str")
#         elif(cus.type == "date"):
#             try:
#                 print("date")
#                 format = "%Y-%m-%d"
#                 datetime.strptime(cus.value, format)
#             except ValueError:

#                 return JSONResponse(status_code = 404, content={"message" : "This is the incorrect date string format. It should be YYYY-MM-DD"})
#         else:
#             return JSONResponse(status_code = 404, content={"type not matching"})



#     #if name exists then update fields. Else make a new entry    
#     if(db.session.query(CustomFields).filter_by(flow_id = cus.flow_id).filter_by(name = cus.name).first() is not None):
#         db.session.query(CustomFields).filter(CustomFields.name == cus.name).update({'value':cus.value})
#         db.session.commit()
#         # return {"message":'custom field updated'}
#         return JSONResponse(status_code = 200, content={"message" : "custom field updated"})
#     else:
#         new_cus = CustomFields(type = cus.type, name = cus.name, value = cus.value,flow_id=cus.flow_id)
#         db.session.add(new_cus)
#         db.session.commit()
#         # return {"message":'success'}
#         return JSONResponse(status_code = 200, content={"message" : "success"})

# @router.post('/create_custom_field')
# async def create_custom_fields(cus : CustomFieldSchema,token = Depends(auth_handler.auth_wrapper)):
#     try:
#         validate_user = await check_user_token(cus.flow_id,token)
#         if (validate_user.status_code != 200):
#             return validate_user
#         x = await create_custom_field(cus)
#         if(x.status_code != 200):
#             return x
#         return JSONResponse(status_code = 200, content = {"message" :"success"})
#     except Exception as e:
#         print("Error in update_connection: ", e)
#         return JSONResponse(status_code=404, content={"message": "can't create custom field"})

# @router.post('/preview')
# async def preview(flow_id : int,token = Depends(auth_handler.auth_wrapper)):
#     """
#     When user clicks on preview, start a preview chat page and return the first/start node.
#     """
#     try:
#         # check_token = await token_validate(user_id, token)
#         # if (check_token == None):
#         #     return JSONResponse(status_code=401, content={"message": "Not authoraized"})
#         #get start node and encode it to JSON
#         start_node = db.session.query(Node.data, Node.flow_id, Node.id, Node.type).filter_by(type = "special").filter_by(flow_id=flow_id).first()#first() and not all(), need to take care of multiple startnodes in the DB
#         start_node = encoders.jsonable_encoder(start_node)
#
#         if(start_node == None):
#             return JSONResponse(status_code=400, content={"message":"Error: No valid node found in this id"})
#
#         #get sub nodes of the obtained start node and convert to JSON
#         sub_nodes = db.session.query(SubNode).filter_by(node_id = start_node['id']).filter_by(flow_id=flow_id).all()
#         sub_nodes = encoders.jsonable_encoder(sub_nodes)
#
#         if(sub_nodes == None):
#             return JSONResponse(status_code=400, content={"message":"Error: No sub node found with this id"})
#
#
#         chat_count = db.session.query(Flow.chats).filter_by(id = flow_id).first()
#         if(chat_count[0] == None):
#             local_count = 0
#         else:
#             local_count = chat_count[0]
#
#         local_count = local_count + 1
#         db.session.query(Flow).filter_by(id = flow_id).update({"chats":local_count})
#         db.session.commit()
#         db.session.close()
#
#         return JSONResponse(status_code=200,content={"start_node": start_node, "sub_nodes":sub_nodes})
#     except Exception as e:
#         print(e)
#         return JSONResponse(status_code=404, content={"message":"Error in preview"})


# @router.post('/send')
# async def send(flow_id : int, my_source_node:str, my_sub_node:str,token = Depends(auth_handler.auth_wrapper)):
#     """
#     Enter the source node and its sub_node and get the next node according to the connections table.
#     """
#     try:
#         validate_user = await check_user_token(flow_id,token)
#         if (validate_user.status_code != 200):
#             return validate_user
#         nodes = []
#         #get current data of current node
#         previous_sub_node = db.session.query(SubNode).filter_by(node_id = my_source_node).filter_by(flow_id=flow_id).filter_by(id = my_sub_node).first()
#         previous_sub_node = {"flow_id":previous_sub_node.flow_id, "node_id":previous_sub_node.node_id, "type": previous_sub_node.type, "data":[previous_sub_node.data], "id":previous_sub_node.id }
#         previous_sub_node = (encoders.jsonable_encoder(previous_sub_node))


#         nn_row = db.session.query(Connections).filter_by(source_node_id = my_source_node).filter_by(sub_node_id = my_sub_node).filter_by(flow_id=flow_id).first()
#         if(nn_row != None):
#             is_end_node = False
#         else:
#             return JSONResponse(status_code=200, content = {"next_node":[], "sub_node":[], "previous_sub_node": previous_sub_node})

#         nn = "chat"#to enter loop
#         type_list = ["button","phone","text","email","number","url","date","file"]
#         #get the next node from Connections table
#         while (nn not in type_list):
#             next_node_row = db.session.query(Connections).filter_by(source_node_id = my_source_node).filter_by(sub_node_id = my_sub_node).filter_by(flow_id=flow_id).first()
#             if(next_node_row == None): break
#             #if the type of node is end node, then complete the chat.
#             if(db.session.query(Connections).filter_by(source_node_id = next_node_row.target_node_id).filter_by(flow_id=flow_id).first() == None):
#                 #get the current count of finish
#                 finished_count = db.session.query(Flow.finished).filter_by(id = flow_id).first()
#                 #the default value is null, in such cases initialize to 0
#                 if(finished_count[0] == None):
#                     local_count = 0
#                 else:
#                     local_count = finished_count[0]
                
#                 #increase by one for present chat
#                 local_count = local_count + 1
#                 #change is_end_node value and update finished chats count
#                 is_end_node = True
#                 db.session.query(Flow).filter_by(id = flow_id).update({"finished":local_count})
#                 db.session.commit()
#                 # db.session.close()
#                 nn
            
#             #get all the details of next node from the ID
#             next_node = db.session.query(Node).filter_by(id = next_node_row.target_node_id).filter_by(flow_id=flow_id).first()

#             #get the sub_nodes of the obtained node
#             # sub_nodes = db.session.query(SubNode).filter_by(node_id = next_node.id).filter_by(flow_id=flow_id).all()
#             # sub_nodes = encoders.jsonable_encoder(sub_nodes)
#             nn = next_node.type
#             my_source_node = next_node.id
#             my_sub_node = str(next_node.id) + "_1b"
#             if nn not in type_list:
#                 my_dict = {"type" : next_node.type, "data":(next_node.data), "id" : next_node.id, "flow_id":next_node.flow_id }
#                 nodes.append(my_dict)
       
#         sub_nodes = []#empty if no buttons

#         if next_node.type in type_list:
#             # my_dict = {"next_node_type" : next_node.type, "next_node_data":(next_node.data), "next_node_id" : next_node.id}
#             # nodes.append(my_dict)
#             sub_nodes = db.session.query(SubNode).filter_by(node_id = next_node.id).filter_by(flow_id=flow_id).all()
#             sub_nodes = encoders.jsonable_encoder(sub_nodes)
            
#         db.session.commit()
#         # db.session.close()
#         return {"next_node":nodes, "sub_node": sub_nodes,"is_end__node" : is_end_node, "previous_sub_node": previous_sub_node}
#     except Exception as e:
#         print("Error at send: ", e)
#         return JSONResponse(status_code=404, content={"message": "Send Chat data : Not Found"})

