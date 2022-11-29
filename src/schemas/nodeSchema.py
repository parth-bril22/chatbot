from typing import Dict, Optional
from pydantic import BaseModel


class CreateNode(BaseModel):
    _id: int  # id is private.
    flow_id: int
    _name: str = "name"
    type: str = "chat"
    destination: str = "name"
    position: Dict = {"top": "0", "left": "0"}
    # all fields from all types are present.
    data: Dict = {
        "nodeData": [
            {
                "text": "",
                "value": "",
                "name": "",
                "type": "",
                "source": "",
                "btn": "",
                "value1": "",
                "value2": "",
                "operator": "",
                "jumpId": "",
                "slack_id": "",
                "from_email": "",
                "to_email": "",
                "subject": "",
                "customEmail": "",
                "assignedAgents": [],
            }
        ]
    }

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class DeleteNode(BaseModel):
    id: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class CreateSubNode(BaseModel):
    _id: str
    node_id: int
    flow_id: int
    type: str
    data: Dict = {"text": ""}

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class UpdateSubNode(BaseModel):
    id: str
    node_id: int
    flow_id: int
    destination: str
    type: str
    data: Dict = {"text": ""}

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class CreateConnection(BaseModel):
    _id: int
    flow_id: int
    _name: Optional[str]
    sub_node_id: str
    source_node_id: int
    target_node_id: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class NodeTypes(BaseModel):
    _id: int
    type: str
    flow_id: int
    data: Dict

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class CreateCustomField(BaseModel):
    _id: int
    flow_id: int
    name: str = ""
    type: str = ""
    value: str = ""

    class Config:
        orm_mode = True
