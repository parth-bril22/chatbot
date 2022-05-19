# build a schema using pydantic
from typing import Dict, Optional
from pydantic import BaseModel


class NodeSchema(BaseModel):
    _id: int #id is made private by the "_" before its name, so frontend need not enter it.
    flow_id: int
    _name: str = "name"
    _path: str = "path"
    type: str = "chat"
    node_type: str = "start_node"
    position: Dict = {"top":"0","left":"0"}

    # all fields from all types are present. Later in api.py, only the relevant fields will be taken into consideration
    properties: Dict = {"text":"","value":"" ,"name" :"", "type":"", "source":"", "message":"", "btn":"","id":"" }

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True

class DelNodeSchema(BaseModel):
    id : int
    class Config:
        orm_mode = True
        underscore_attrs_are_private = True

class SubNodeSchema(BaseModel):
    _id : int
    node_id : int
    flow_id: int
    name : str
    properties : Dict = {"text":""}
    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
class ConnectionSchema(BaseModel):
    _id: int
    flow_id: int
    _name: Optional[str]
    sub_node_id: int
    source_node_id: int
    target_node_id: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
    


class NodeTypeSchema(BaseModel):
    _id: int
    type: str
    flow_id:int
    properties: Dict

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True

class CustomFieldSchema(BaseModel):
    _id: int
    flow_id: int
    name: str = ""
    type: str = ""
    value: str = ""

    class Config:
        orm_mode = True
