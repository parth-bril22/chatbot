from src.schemas.flowSchema import *
from ..schemas.nodeSchema import *
from ..models.node import Node, NodeType , Connections,CustomFieldTypes, CustomFields, SubNode
from ..models.flow import Flow
from fastapi.responses import JSONResponse



from fastapi import APIRouter, status, HTTPException ,encoders , Response
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
                    Response(status_code = 204)
                else:
                    #check if there is "args" key in the json
                    if "args" in prop_value_json[ele]:
                        #iterate over all conditions(==,<,...) in "args"
                        for all_symbols in prop_value_json[ele]["args"]:
                            #all_symbols_keys returns dict_keys object, so we convert it into list and get the first(and only) element to get the key
                            symbol = list(all_symbols.keys())[0]

                            if symbol not in ["==", "<", ">"] or len(list(all_symbols.keys())) != 1:
                                # return {"message" : "Enter conditional logic correctly", "at": (ele)}
                                Response(status_code = 204)
                            else:
                                #get all args, ie arg1 and arg2
                                all_args = (list((all_symbols[symbol]).keys()))
                                for arg in all_args:
                                    if arg not in ["arg1", "arg2"]:
                                        # return {"message" : "Enter conditional logic correctly", "at": (ele,symbol)}
                                        Response(status_code = 204)
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
                                            Response(status_code = 204)
                    else:
                        # return {"message" : "Enter conditional logic correctly", "at":""}
                        Response(status_code = 204)
    return True


async def check_property_dict(node: Node, prop : Dict, keys : List):
    
    prop_dict = {k: v for k, v in prop.items() if k in keys}
    print(prop_dict)
    #necessary fields not filled
    if (len(prop_dict) != len(keys)):
        return False, Response(status_code = 204)
    
    #For Empty entries return error. string.strip() can be used for spaces later.
    if "" in node.dict().values( ) or "" in prop_dict.values(): 
        return False, Response(status_code = 204)
    
    # if type is conditional logic, then get the "value" field
    if "value" in prop_dict.keys() and node.type == "conditional_logic": 
            #load string in "value" as json
            prop_value_json = json.loads(prop_dict['value'])
            logic_check = await check_conditional_logic(prop_value_json)
            if(logic_check != True):
                return False, logic_check
    
    return True, prop_dict

async def check_node_details(node:NodeSchema):
     #check if the "type" of node is actually present in the nodetype table
    print("-----------")
    node_type_params = db.session.query(NodeType).filter(NodeType.type == node.type).first()
    #if not, return error
    if(node_type_params == None):
        return JSONResponse(status_code = 404, content = {"message": "incorrect type field"}), node.properties
    props = []
    print(node.properties['nodeData'])
    print(node_type_params)
    #make a dict of properties(prop_dict) which will take only the relevant key-value pairs according to the type of node
    for property in node.properties['nodeData']:
        bool_val, prop_dict = await check_property_dict(node, property,list(node_type_params.params.keys()))
        if(bool_val == False):
            return prop_dict
        else:
            props.append(prop_dict)
    #  "{\"||\" : {\"args\":[{\"==\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}, {\"<\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}]}}"
    return JSONResponse(status_code=200), props

#create a new node
# @router.post('/create_node')
async def create_node(node:NodeSchema):
    """
    Insert a node into the database. Returns 200 if success, error code and description otherwise.
    """
    print(node)
    #check if values in node are correct
    node_check, node_properties = await check_node_details(node)
    print(node_check.status_code)
    print(node_properties)
    if(node_check.status_code != 200):
        return node_check

    #get dictionary of node Can be changed to properties  
    prop_dict = node_properties

    #set unique name og length(4 * 2 = 8)
    my_name = secrets.token_hex(4)
    # node_data = {"nodeData" : json.dumps(prop_dict)}
    # make a new object of type Node with all the entered details
    new_node = Node(name = my_name, type = node.type, properties = prop_dict , position = json.dumps(node.position), flow_id = node.flow_id)
    #id,name and path are made private by the "_" before name in schemas.py, so frontend need not enter them.
    db.session.add(new_node)
    db.session.commit()


    # if(db.session.query(SubNode).filter_by(node_id = new_node.id).filter_by(flow_id = new_node.flow_id).filter_by(id = "$success") == None):
    #make default sub_node for all nodes
    for item in prop_dict:
        print(item)
        new_sub_node = SubNode(node_id = new_node.id, flow_id = node.flow_id, properties = item)
        db.session.add(new_sub_node)
    db.session.commit()
    db.session.close()
    # print(json.loads(new_node.properties))
    # return {"message": "success"}
    return JSONResponse(status_code = 200, content = {"message": "success"})

@router.post('/create_node')
async def create_nodes(nodes : List[NodeSchema]):
    for item in nodes:
        x = await create_node(item)
        if(x.status_code != 200):
            return x
    return JSONResponse(status_code = 200, content = {"message": "success"})

@router.post('/get_node')
async def get_node(node_id: int, flow_id : int):
    my_node = db.session.query(Node).filter_by(flow_id=flow_id).filter_by(id = node_id).first()
    if(my_node == None):
        return JSONResponse(status_code=200, content = {"message":"Node not found"})
    else:
        return JSONResponse(status_code = 200, content = {"id" : my_node.id, "type" : my_node.type, "position":json.loads(my_node.position), "data": {"label" : "NEW NODE", "nodeData":json.loads(my_node.properties)} })

@router.delete('/delete_node')
async def delete_node(node_id : str, flow_id:int):
    try:
        # print([value[0] for value in db.session.query(Node.id)])
        node_in_db = db.session.query(Node).filter_by(flow_id = flow_id).filter_by(id = node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})

        # delete node from node table
        node_in_db.delete()
        #delete all connections of deleted node from connections table(if matched at source node or target node)
        db.session.query(Connections).filter((Connections.source_node_id == node_id) | (Connections.target_node_id == node_id)).delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {'message': 'Node deleted'})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})  

@router.post('/update_node')
async def update_node(node_id:str,my_node:NodeSchema):
    try:
        
        #check if the node_id is in the database
        node_in_db = db.session.query(Node).filter_by(id = node_id).filter_by(flow_id=my_node.flow_id)
        
        #if there is no node with given id, return 404
        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Node not found"})
        

        #get jsonresponse(w status code) and dict with relevant fields only
        node_check, node_properties = await check_node_details(my_node)
        #check for errors
        if(node_check.status_code != 200):
            return node_check
    
        #update node properties
        db.session.query(Node).filter(Node.id == node_id).filter_by(flow_id=my_node.flow_id).update({'properties' : node_properties})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code = 200, content = {"message":"success"})
    except:
         return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"}) 

@router.post("/add_sub_node")
async def add_sub_node(sub:SubNodeSchema):
    # try:
    #make default sub_node for all nodes
    # new_sub_node = SubNode(node_id = new_node.id, name = "$default", flow_id = node.flow_id)
    # db.session.add(new_sub_node)
    node_in_db = db.session.query(Node).filter_by(id = sub.node_id).filter_by(flow_id=sub.flow_id)
    if(node_in_db.first() == None):
        return JSONResponse(status_code=404, content={"message":"Node or flow id not found"})
    # node_in_db.delete()
    new_sub_node = SubNode(node_id = sub.node_id,properties = json.dumps(sub.properties),flow_id = sub.flow_id)
    db.session.add(new_sub_node)
    db.session.commit()
    db.session.close()
    return JSONResponse(status_code = 200, content = {"message" : "Sub node addedd"})
    # except:
        # return JSONResponse(status_code=404, content={"message":"Node not present in db"})  

@router.delete('/delete_sub_node')
async def delete_sub_node(sub_node_id : str, flow_id:int):
    try:
        # print([value[0] for value in db.session.query(Node.id)])
        node_in_db = db.session.query(SubNode).filter_by(flow_id = flow_id).filter_by(id = sub_node_id)

        if(node_in_db.first() == None):
            return JSONResponse(status_code=404, content={"message":"Sub Node not found"})

        # delete node from node table
        node_in_db.delete()
        #delete all connections of deleted node from connections table(if matched at source node or target node)
        db.session.query(Connections).filter(Connections.sub_node_id == sub_node_id).delete()
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code = 200, content = {'message': 'Sub Node deleted'})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter sub_node_id correctly"})  
# @router.post('/create_connection')
async def create_connection(conn : ConnectionSchema):
    #if empty, set $success as default
    if conn.sub_node_id == "" : conn.sub_node_id = "$success"

    try:
        source_node_exists = db.session.query(Node).filter((Node.id == conn.source_node_id)).first()
        target_node_exists = db.session.query(Node).filter((Node.id == conn.target_node_id)).first()

        if(source_node_exists == None or target_node_exists == None):
            return JSONResponse(status_code = 404, content = {"message" : "Node not found"})
    except:
        return JSONResponse(status_code=404, content={"message":"Please enter node_id correctly"})

    if "" in conn.dict().values( ):
        # return {"message" : "please leave no field empty"}  
        Response(status_code = 204)

    #set my_name variable which will later be used to set the name
    my_name = "c_" + str(conn.source_node_id) + "_" + str(conn.sub_node_id) + "-" + str(conn.target_node_id)

    if(conn.source_node_id == conn.target_node_id):
        # return {"message" : "Source and Target node cannot be the same"}
        return JSONResponse(status_code = 406, content={"message":"Source and Target node cannot be the same"})

    #if the (source_node's + subnode's) connection exists somewhere, update other variables only. Else make a new entry
    if(db.session.query(Connections).filter_by(flow_id=conn.flow_id).filter_by(source_node_id= conn.source_node_id).filter_by(sub_node_id = conn.sub_node_id).first() is not None):
        db.session.query(Connections).filter(Connections.source_node_id == conn.source_node_id).filter(Connections.sub_node_id == conn.sub_node_id).\
        update({'target_node':conn.target_node_id, 'name' : my_name})
    else:
        new_conn = Connections(sub_node_id = conn.sub_node_id, source_node_id = conn.source_node_id, target_node_id = conn.target_node_id, name = my_name,flow_id= conn.flow_id)
        db.session.add(new_conn)

    db.session.commit()
    # return {"message":'success'}
    return JSONResponse(status_code = 200, content = {"message": "success"})

         
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
    if(db.session.query(CustomFields).filter_by(flow_id = cus.flow_id).filter_by(name = cus.name).first() is not None):
        db.session.query(CustomFields).filter(CustomFields.name == cus.name).update({'value':cus.value})
        db.session.commit()
        # return {"message":'custom field updated'}
        return JSONResponse(status_code = 200, content={"message" : "custom field updated"})
    else:
        new_cus = CustomFields(type = cus.type, name = cus.name, value = cus.value,flow_id=cus.flow_id)
        db.session.add(new_cus)
        db.session.commit()
        # return {"message":'success'}
        return JSONResponse(status_code = 200, content={"message" : "success"})

async def create_custom_fields(cus : List[CustomFieldSchema]):
    for item in cus:
        x = await create_custom_field(item)
        if(x.status_code != 200):
            return x
    return JSONResponse(status_code = 200, content = {"message" :"success"})

@router.post('/preview')
async def preview(flow_id : int):
    """
    When user clicks on preview, start a preview chat page and return the first/start node.
    """
    try:

        #get start node and encode it to JSON
        start_node = db.session.query(Node.properties, Node.flow_id, Node.id, Node.type).filter_by(type = "special").filter_by(flow_id=flow_id).first()#first() and not all(), need to take care of multiple startnodes in the DB
        start_node = encoders.jsonable_encoder(start_node)

        if(start_node == None):
            return JSONResponse(status_code=400, content={"message":"Error: No valid node found in this id"})
        
        #get sub nodes of the obtained start node and convert to JSON
        sub_nodes = db.session.query(SubNode).filter_by(node_id = start_node['id']).filter_by(flow_id=flow_id).all()
        sub_nodes = encoders.jsonable_encoder(sub_nodes)

        if(sub_nodes == None):
            return JSONResponse(status_code=400, content={"message":"Error: No sub node found with this id"})


        chat_count = db.session.query(Flow.chats).filter_by(id = flow_id).first()
        if(chat_count[0] == None):
            local_count = 0
        else:
            local_count = chat_count[0]
        
        local_count = local_count + 1
        db.session.query(Flow).filter_by(id = flow_id).update({"chats":local_count})
        db.session.commit()
        db.session.close()

        return JSONResponse(status_code=200,content={"start_node": start_node, "sub_nodes":sub_nodes})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"message":"Error in preview"})



@router.post('/send')
async def send(flow_id : int, my_source_node:str, my_sub_node:str):
    """
    Enter the source node and its sub_node and get the next node according to the connections table.
    """
    try:
        is_end_node = False
        # print(db.session.query(Node.node_type).filter_by(id=my_source_node).first()[0])

        #get the next node from Connections table
        next_node_row = db.session.query(Connections).filter_by(source_node_id = my_source_node).filter_by(sub_node_id = my_sub_node).filter_by(flow_id=flow_id).first()
        
        #if the type of node is end node, then complete the chat.
        if(db.session.query(Connections).filter_by(source_node_id = next_node_row.target_node_id).filter_by(sub_node_id = my_sub_node).filter_by(flow_id=flow_id).first() == None):
            #get the current count of finish
            finished_count = db.session.query(Flow.finished).filter_by(id = flow_id).first()
            #the default value is null, in such cases initialize to 0
            if(finished_count[0] == None):
                local_count = 0
            else:
                local_count = finished_count[0]
            
            #increase by one for present chat
            local_count = local_count + 1
            #change is_end_node value and update
            is_end_node = True
            db.session.query(Flow).filter_by(id = flow_id).update({"finished":local_count})
            db.session.commit()
        
        #get all the details of next node from the ID
        next_node = db.session.query(Node).filter_by(id = next_node_row.target_node_id).filter_by(flow_id=flow_id).first()
        #get the sub_nodes of the obtained node
        sub_nodes = db.session.query(SubNode).filter_by(node_id = next_node.id).filter_by(flow_id=flow_id).all()
        sub_nodes = encoders.jsonable_encoder(sub_nodes)
        db.session.commit()
        # db.session.close()
        return {"next_node_type" : next_node.type, "next_node_properties":json.loads(next_node.properties), "next_node_row" : next_node.id, "next_node_sub_nodes": sub_nodes, "is_end_node": is_end_node}
    except Exception as e:
        print(e)
        return JSONResponse(status_code=404, content={"message": "Send Chat data : Not Found"})
    
