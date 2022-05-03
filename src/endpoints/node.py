from ..schemas.nodeSchema import *
from ..models.node import *


from fastapi import FastAPI, Body
from fastapi import APIRouter
import uvicorn 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
import datetime
import secrets
from ast import literal_eval
from fastapi_sqlalchemy import DBSessionMiddleware, db

# import copy
# doc.config = copy.deepcopy(doc.config)
#https://amercader.net/blog/beware-of-json-fields-in-sqlalchemy/

# from schema import CustomFieldSchema, NodeSchema, ConnectionSchema
# from models import Node, NodeType, Connections, CustomFields, CustomFieldTypes, Diagram


#start sqlalchemy engine, connect to database and start db.session

router = APIRouter(
    prefix="/node",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)

#create a new node
@router.post('/create_node')
async def create_node(node:NodeSchema):
    #use of path??

    #check if the "type" of node is actually present in the nodetype table
    prop = db.session.query(NodeType).filter(NodeType.type == node.type).first()
    #if not, return message
    if(prop == None):
        return {"message": "incorrect type field"}
    
    #make a dict which will take only the relevant key-value pairs according to the type of node
    prop_dict = {k: v for k, v in node.properties.items() if k in prop.params.keys()}

    if (len(prop_dict) != len(prop.params.keys())):#necessary fields not filled
        return {"message" : "please enter all fields"}
    if "" in node.dict().values( ) or "" in prop_dict.values(): #For Empty entries.
        return {"message" : "please leave no field empty"}
    
    if "value" in prop_dict.keys() and node.type == "button": # for json in button
            prop_value_json = json.loads(prop_dict['value'])
            if(len(prop_value_json.keys( )) == 0 ):
                return {"message" : "please fill all fields"}
            else:
                for ele in list(prop_value_json.keys()): 
                        if ele not in ["||", "&&", ">", "<", "!"]:
                            return {"message" : "please fill || or && or > or < or ! only"}
                        else:#TODO:complete <=>...validation
                            if "args" in prop_value_json['||']:
                                print(prop_value_json['||']["args"][0]["=="])
                                 #"{\"||\" : {\"args\":[{\"==\":{\"arg1\":\"1\", \"arg2\" : \"2\"}}]}}"
                            # else:
                                # return {"message" : "no args"}
    
    #set unique name
    my_name = secrets.token_hex(4)

    # make a new object of type Node with all the entered details
    new_node = Node(name = my_name, path = my_name, type = node.type, node_type = node.node_type, properties = json.dumps(prop_dict), position = json.dumps(node.position))
    #id,name and path are made private by the "_" before name in schemas.py, so frontend need not enter them.

    db.session.add(new_node)
    db.session.commit()
    return {"message": "success"}


@router.post('/create_connection')
async def create_connection(conn : ConnectionSchema) :
    #if empty, set $success as default
    if conn.sub_node == "" : conn.sub_node = "$success"
    
    if "" in conn.dict().values( ):
        return {"message" : "please leave no field empty"}  

    #set my_name variable which will later be used to set the name
    my_name = "c_" + conn.source_node + "_" + conn.sub_node + "-" + conn.target_node

    if(conn.source_node == conn.target_node):
        return {"message" : "Source and Target node cannot be the same"}

    #if the (source_node's + subnode's) connection exists somewhere, update other variables only. Else make a new entry
    if(db.session.query(Connections).filter_by(source_node = conn.source_node).filter_by(sub_node = conn.sub_node).first() is not None):
        db.session.query(Connections).filter(Connections.source_node == conn.source_node).filter(Connections.sub_node == conn.sub_node).\
        update({'target_node':conn.target_node, 'name' : my_name})
    else:
        new_conn = Connections(sub_node = conn.sub_node, source_node = conn.source_node, target_node = conn.target_node, name = my_name)
        db.session.add(new_conn)

    db.session.commit()
    return {"message":'success'}


@router.post('/create_custom_field')
async def create_custom_field(cus : CustomFieldSchema):

    #check if type exists in the customfieldtypes table
    prop = db.session.query(CustomFieldTypes).filter(CustomFieldTypes.type == cus.type).first()
    
    if(prop == None):
        return {"message": "incorrect type field"}
    if "" in cus.dict().values( ):
        return {"message" : "please leave no field empty"}  

    #check if type entered and value's datatype matches

    try:
        ip_type = type(literal_eval(cus.value))
        if(cus.type == "number"):
            my_type = str(ip_type).split(" ")[-1][:-1].strip("\'")
            print(my_type)
            if my_type != "int" and my_type != "float":
                return {"please check your number"}
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
                return {"message" : "This is the incorrect date string format. It should be YYYY-MM-DD"}
        else:
            return {"message": "type not matching"}


    
    #if name exists then update fields. Else make a new entry    
    if(db.session.query(CustomFields).filter_by(name = cus.name).first() is not None):
        db.session.query(CustomFields).filter(CustomFields.name == cus.name).update({'value':cus.value})
        db.session.commit()
        return {"message":'custom field updated'}
    else:
        new_cus = CustomFields(type = cus.type, name = cus.name, value = cus.value)
        db.session.add(new_cus)
        db.session.commit()
        return {"message":'success'}

# if __name__ == "__main__":
#     uvicorn.run(router)