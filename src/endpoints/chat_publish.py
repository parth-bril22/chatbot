from src.endpoints.flow import get_diagram
from src.schemas.flowSchema import *
from ..schemas.nodeSchema import *
from ..models.node import Node, NodeType , Connections,CustomFieldTypes, CustomFields, SubNode
from ..models.flow import Flow
from fastapi.responses import JSONResponse

from fastapi import APIRouter, Body, status, HTTPException ,encoders, Response
from typing import List
import json
import datetime
import secrets
from ast import literal_eval
from fastapi_sqlalchemy import db


from fastapi import Depends, HTTPException
from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()


router = APIRouter(
    prefix="/chat_publish/v1",
    tags=["Chat Publish"],
    responses={404: {"description": "Not found"}},
)




@router.post('/preview')
async def preview(flow_id : int):
    """
    When user clicks on preview, start a preview chat page and return the first/start node.
    """
    try:
        diagram = await get_diagram(flow_id)
        nodes = diagram['nodes']
        sub_nodes = diagram['nodes']

        #get start node
        start_node = None
        for node in nodes:
            if(node['type'] == "special" and node['flow_id'] == flow_id):
                start_node = node
        
        if(start_node == None):#NEED TO CHECK THIS FOR JSON
            return JSONResponse(status_code=400, content={"message":"Error: No valid node found in this id"})
        
        #get sub nodes of the obtained start node and convert to JSON
        all_sns_to_include = []
        for sub_node in sub_nodes:
            if(sub_node['id'] == start_node['id'] and sub_node['flow_id'] == flow_id):
                all_sns_to_include.append(sub_node)

        if(all_sns_to_include == None or all_sns_to_include == None):
            return JSONResponse(status_code=400, content={"message":"Error: No sub node found with this id"})

        #Check & Count number of chats initiated
        chat_count = db.session.query(Flow.chats).filter_by(id = flow_id).first()#can keep this same

        if(chat_count[0] == None):
            local_count = 0
        else:
            local_count = chat_count[0]
     
        #increase count of chats initialized
        local_count = local_count + 1
        db.session.query(Flow).filter_by(id = flow_id).update({"chats":local_count})

        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=200,content={"start_node": (start_node), "sub_nodes":all_sns_to_include})
    except Exception as e:
        print("Error in preview: ", e)
        return JSONResponse(status_code=404, content={"message":"Error in preview"})


@router.post('/send')
async def send(flow_id : int, my_source_node:str, my_sub_node:str):
    """
    Enter the source node and its sub_node and get the next node according to the connections table.
    """
    try:
        diagram = await get_diagram(flow_id)
        nodes = diagram['nodes']
        sub_nodes = diagram['nodes']
        connections = diagram['connections']
        #get current data of current node
        previous_sub_node = None
        for sub_node in sub_nodes:
            if((sub_node['flow_id'] == flow_id) and (str(sub_node['id']) == my_source_node)):
                
                for nodeData in sub_node['data']['nodeData']:
                    if(nodeData['id'] == my_sub_node):
                        previous_sub_node = sub_node

        
        previous_sub_node = {"flow_id":previous_sub_node['flow_id'], "node_id":previous_sub_node['id'], "type": previous_sub_node['type'], "data":[previous_sub_node['data']], "id":previous_sub_node['id'] }
        # previous_sub_node = (encoders.jsonable_encoder(previous_sub_node))
        # previous_node = (encoders.jsonable_encoder(previous_node)

       
        nn_row = None
        for conn in connections:
            print(conn)
            if((str(conn['source']) == str(my_source_node)) and (str(conn['sourceHandle']) == str((my_sub_node)))):
                if(conn['flow_id'] == flow_id):
                    nn_row = conn

        if(nn_row != None):
            is_end_node = False
        else:
            return JSONResponse(status_code=200, content = {"next_node":[], "sub_node":[], "previous_sub_node": previous_sub_node})
        next_node = None
        nn = "chat"#to enter loop
        #get the next node from Connections table
        while (nn != "button" and nn!= "input"):
            # next_node_row = db.session.query(Connections).filter_by(source_node_id = my_source_node).filter_by(sub_node_id = my_sub_node).filter_by(flow_id=flow_id).first()
            next_node_row = None
            for conn in connections:
                if(str(conn['source']) == str(my_source_node) and str(conn['sourceHandle']) == str(my_sub_node)):
                    if(conn['flow_id'] == flow_id):
                        next_node_row = conn
                        

        
            if(next_node_row == None):
                print("Ohho")
                break
            #if the type of node is end node, then complete the chat.

            finished_count = []
            for conn in connections:
                if((conn['source'] == next_node_row['target'] and conn['flow_id'] == flow_id) == None):
                    finished_count = db.session.query(Flow.finished).filter_by(id = flow_id).first()
                print(finished_count)
                #the default value is null, in such cases initialize to 0
                if(finished_count == []):
                    local_count = 0
                else:
                    local_count = finished_count[0]
                
                #increase by one for present chat
                local_count = local_count + 1
                #change is_end_node value and update finished chats count
                is_end_node = True
                db.session.query(Flow).filter_by(id = flow_id).update({"finished":local_count})
                db.session.commit()
                # db.session.close()
                # nn = "button"
                nn = "button"
            print(next_node_row)
            #get all the details of next node from the ID
            for node in nodes:
                
                print(node['id'] , next_node_row['target'] , node['flow_id'] , flow_id)
                if(node['id'] == next_node_row['target'] and node['flow_id'] == flow_id):
                    next_node = node
            print(next_node)
            #get all the details of next node from the ID
            


            #get the sub_nodes of the obtained node
            nn = next_node['type']
            my_source_node = next_node['id']
            my_sub_node = str(next_node['id']) + "_1b"
            if(nn != "button" and nn != "input"):
                my_dict = {"type" : next_node['type'], "data":(next_node['data']), "id" : next_node['id'], "flow_id":next_node['flow_id'] }
                nodes.append(my_dict)
       
        sns_to_include = []#empty if no buttons

        if(next_node['type'] == "button" or next_node['type'] == "input" ):
            # my_dict = {"next_node_type" : next_node.type, "next_node_data":(next_node.data), "next_node_id" : next_node.id}
            # nodes.append(my_dict)
            # sub_nodes = db.session.query(SubNode).filter_by(node_id = next_node.id).filter_by(flow_id=flow_id).all()
            for sub_node in sub_nodes:
                if (sub_node['id'] == next_node['id'] and sub_node['flow_id'] == flow_id):
                    sns_to_include.append(sub_node)

        db.session.commit()
        # db.session.close()
        return {"next_node":nodes, "sub_node": sns_to_include,"is_end__node" : is_end_node, "previous_sub_node": previous_sub_node}
    except Exception as e:
        print("Error at send: ", e)
        return JSONResponse(status_code=404, content={"message": "Send Chat data : Not Found"})