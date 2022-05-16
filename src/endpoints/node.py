from ..schemas.nodeSchema import *
from ..models.node import Node, NodeType , Connections,CustomFieldTypes, CustomFields, SubNode
from fastapi.responses import JSONResponse


from fastapi import APIRouter, status, HTTPException
from typing import List
import json
import datetime
import secrets
from ast import literal_eval
from fastapi_sqlalchemy import db

router = APIRouter(
    prefix="/node/v1",
    tags=["Node"],
    responses={404: {"description": "Not found"}},
)

async def check_conditional_logic(prop_value_json : json):
    """
    Input format:
    "{\"||\" : {\"args\":[{\"==\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}, {\"<\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}]}}"

    Check if json is empty or not
    then check at five levels: 
    via if /else: 1)||, 2)args, 3) "==", 4)arg1,
    via try/except: 5) 1
    """
    #if json is empty, return error
    if(len(prop_value_json.keys( )) == 0 ):
        # return {"message" : "please fill all fields"}
        raise HTTPException(status_code = status.HTTP_204_NO_CONTENT, )
        
    else:
        #else we will check if the (or,and,etc) entered are correct
        for ele in list(prop_value_json.keys()): 
                if ele not in ["||", "&&", "!"]:
                    # return {"message" : "please fill || or && or > or < or ! only"}
                    # return JSONResponse(status_code = 404, content={'Error': "Please Upload .PNG files only"})
                    raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
                else:
                    #check if there is "args" key in the json
                    if "args" in prop_value_json[ele]:
                        #iterate over all conditions(==,<,...) in "args"
                        for all_symbols in prop_value_json[ele]["args"]:
                            #all_symbols_keys returns dict_keys object, so we convert it into list and get the first(and only) element to get the key
                            symbol = list(all_symbols.keys())[0]

                            if symbol not in ["==", "<", ">"] or len(list(all_symbols.keys())) != 1:
                                # return {"message" : "Enter conditional logic correctly", "at": (ele)}
                                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
                            else:
                                #get all args, ie arg1 and arg2
                                all_args = (list((all_symbols[symbol]).keys()))
                                for arg in all_args:
                                    if arg not in ["arg1", "arg2"]:
                                        # return {"message" : "Enter conditional logic correctly", "at": (ele,symbol)}
                                        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
                                    else:
                                        try:
                                            #load value of each arg
                                            value = json.loads(all_symbols[symbol][arg])
                                            #TODO:we will check whether the entered value are numeric or not by adding 1 as only numbers can be added to numbers.
                                            value + 1
                                            #The existing methods&libraries check only for float or/and int, making checking for other data types difficult.
                                            #OR regex can be used
                                        except:
                                            # return {"message" : "Enter conditional logic correctly", "at": (ele,symbol,arg)}
                                            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
                    else:
                        # return {"message" : "Enter conditional logic correctly", "at":""}
                        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    return True


#create a new node
# @router.post('/create_node')
async def create_node(node:NodeSchema):
    #use of path??

    #check if the "type" of node is actually present in the nodetype table
    prop = db.session.query(NodeType).filter(NodeType.type == node.type).first()
    #if not, return message
    if(prop == None):
        return JSONResponse(status_code = 404, content = {"message": "incorrect type field"})
    
    #make a dict which will take only the relevant key-value pairs according to the type of node
    prop_dict = {k: v for k, v in node.properties.items() if k in prop.params.keys()}

    if (len(prop_dict) != len(prop.params.keys())):#necessary fields not filled
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    if "" in node.dict().values( ) or "" in prop_dict.values(): #For Empty entries.
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        
    
    if "value" in prop_dict.keys() and node.type == "conditional_logic": # if type is conditional logic, then get the "value" field
            prop_value_json = json.loads(prop_dict['value'])#load string in "value" as json
            logic_check = await check_conditional_logic(prop_value_json)
            if(logic_check != True):
                return logic_check
    
    #set unique name og length(4 * 2 = 8)
    my_name = secrets.token_hex(4)

    # make a new object of type Node with all the entered details
    new_node = Node(name = my_name, path = my_name, type = node.type, node_type = node.node_type, properties = json.dumps(prop_dict), position = json.dumps(node.position))
    #id,name and path are made private by the "_" before name in schemas.py, so frontend need not enter them.
    db.session.add(new_node)
    db.session.commit()
    return JSONResponse(status_code = 200, content = {"message": "success"})

@router.post('/create_nodes')
async def create_nodes(nodes : List[NodeSchema]):
    for item in nodes:
        x = await create_node(item)
        if(x.status_code != 200):
            return x
    return JSONResponse(status_code = 200, content = {"message": "success"})

# Delete node by user
# @router.delete('/delete_node')
# async def delete_node(node_id :int):
#     if node_id in [value[0] for value in db.session.query(Node.id)]:
#         db.session.query(Node).filter_by(id = node_id).delete()
#         db.session.commit()
#         db.session.close()
#     else: 
#         return JSONResponse(status_code = 404, content = {'message': 'id not found'})
#     return JSONResponse(status_code = 200, content = {'message': 'Node deleted'})

@router.delete('/delete_node')
async def delete_node(node_id : str):
    try:
        # print([value[0] for value in db.session.query(Node.id)])
        node_in_db = db.session.query(Node).filter_by(id = node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})

        # delete node from node table
        node_in_db.delete()
        #delete all connections of deleted node from connections table(if matched at source node or target node)
        db.session.query(Connections).filter((Connections.source_node == node_id) | (Connections.target_node == node_id)).delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {'message': 'Node deleted'})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})  

@router.post("/add_sub_node")
async def add_sub_node(sub:SubNodeSchema):
    try:
        new_sub_node = SubNode(node_id = sub.node_id, name = sub.name,properties = json.dumps(sub.properties))
        db.session.add(new_sub_node)
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {"message" : "Sub node addedd"})
    except:
        return JSONResponse(status_code=404, content={"message":"Node not present in db"})  



    
# @router.post('/create_connection')
async def create_connection(conn : ConnectionSchema):
    #if empty, set $success as default
    if conn.sub_node == "" : conn.sub_node = "$success"


    try:
        source_node_exists = db.session.query(Node).filter((Node.id == conn.source_node)).first()
        target_node_exists = db.session.query(Node).filter((Node.id == conn.target_node)).first()

        if(source_node_exists == None or target_node_exists == None):
            return JSONResponse(status_code = 404, content = {"message" : "Node not found"})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})

    if "" in conn.dict().values( ):
        # return {"message" : "please leave no field empty"}  
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

    #set my_name variable which will later be used to set the name
    my_name = "c_" + conn.source_node + "_" + conn.sub_node + "-" + conn.target_node

    if(conn.source_node == conn.target_node):
        # return {"message" : "Source and Target node cannot be the same"}
        return JSONResponse(status_code = 406, content={"message":"Source and Target node cannot be the same"})

    #if the (source_node's + subnode's) connection exists somewhere, update other variables only. Else make a new entry
    if(db.session.query(Connections).filter_by(source_node = conn.source_node).filter_by(sub_node = conn.sub_node).first() is not None):
        db.session.query(Connections).filter(Connections.source_node == conn.source_node).filter(Connections.sub_node == conn.sub_node).\
        update({'target_node':conn.target_node, 'name' : my_name})
    else:
        new_conn = Connections(sub_node = conn.sub_node, source_node = conn.source_node, target_node = conn.target_node, name = my_name)
        db.session.add(new_conn)

    db.session.commit()
    # return {"message":'success'}
    return JSONResponse(status_code = 200, content = {"message": "success"})


async def check_node_details(node:NodeSchema):
    prop = db.session.query(NodeType).filter(NodeType.type == node.type).first()
    #if not, return message
    if(prop == None):
        return JSONResponse(status_code = 404, content = {"message": "incorrect type field"})
    
    #make a dict which will take only the relevant key-value pairs according to the type of node
    prop_dict = {k: v for k, v in node.properties.items() if k in prop.params.keys()}

    if (len(prop_dict) != len(prop.params.keys())):#necessary fields not filled
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    if "" in node.dict().values( ) or "" in prop_dict.values(): #For Empty entries.
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        
    
    if "value" in prop_dict.keys() and node.type == "conditional_logic": # if type is conditional logic, then get the "value" field
            prop_value_json = json.loads(prop_dict['value'])#load string in "value" as json
            logic_check = await check_conditional_logic(prop_value_json)
            if(logic_check != True):
                return logic_check
                #  "{\"||\" : {\"args\":[{\"==\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}, {\"<\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}]}}"
    return JSONResponse(status_code=200), prop_dict

@router.post('/update_node')
async def update_node(node_id:str,my_node:NodeSchema):
    try:
        
        #check if the node_id is in the database
        node_in_db = db.session.query(Node).filter_by(id = node_id)
        #if there is no node with given id, return 404
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})
        

        #get jsonresponse(w status code) and dict with relevant fields only
        node_check, node_properties = await check_node_details(my_node)
        #check for errors
        if(node_check.status_code != 200):
            return node_check
    
        #update node properties
        db.session.query(Node).filter(Node.id == node_id).update({'properties' : node_properties})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except:
         return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})  
         
@router.post('/create_connection')
async def create_connections(conns : List[ConnectionSchema]):
    for conn in conns:
        x = await create_connection(conn)
        if(x.status_code != 200):
            return x
    return JSONResponse(status_code = 200, content = {"message" :"success"})

@router.post('/create_custom_field')
async def create_custom_field(cus : CustomFieldSchema):

    #check if type exists in the customfieldtypes table
    prop = db.session.query(CustomFieldTypes).filter(CustomFieldTypes.type == cus.type).first()
    
    if(prop == None):
        # return {"message": "incorrect type field"}
        raise HTTPException(status_code = status.HTTP_204_NO_CONTENT)
    if "" in cus.dict().values( ):
        # return {"message" : "please leave no field empty"}  
        raise HTTPException(status_code = status.HTTP_204_NO_CONTENT)

    #check if type entered and value's datatype matches

    try:
        ip_type = type(literal_eval(cus.value))
        if(cus.type == "number"):
            my_type = str(ip_type).split(" ")[-1][:-1].strip("\'")
            print(my_type)
            if my_type != "int" and my_type != "float":
                # return {"please check your number"}
                return JSONResponse(status_code = 404, content={"message": "please check your number"})
        else:
            raise ValueError
    except (ValueError, SyntaxError):# error occurs when type is string
        if cus.type == "text":
            print("str")
        elif(cus.type == "date"):
            try:
                print("date")
                format = "%Y-%m-%d"
                datetime.datetime.strptime(cus.value, format)
            except ValueError:
                # return {"message" : "This is the incorrect date string format. It should be YYYY-MM-DD"}
                return JSONResponse(status_code = 404, content={"message" : "This is the incorrect date string format. It should be YYYY-MM-DD"})
        else:
            # return {"message": "type not matching"}
            return JSONResponse(status_code = 404, content={"type not matching"})


    
    #if name exists then update fields. Else make a new entry    
    if(db.session.query(CustomFields).filter_by(name = cus.name).first() is not None):
        db.session.query(CustomFields).filter(CustomFields.name == cus.name).update({'value':cus.value})
        db.session.commit()
        # return {"message":'custom field updated'}
        return JSONResponse(status_code = 200, content={"message" : "custom field updated"})
    else:
        new_cus = CustomFields(type = cus.type, name = cus.name, value = cus.value)
        db.session.add(new_cus)
        db.session.commit()
        # return {"message":'success'}
        return JSONResponse(status_code = 200, content={"message" : "success"})


