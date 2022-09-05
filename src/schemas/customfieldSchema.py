from typing import Dict
from pydantic import BaseModel

class GlobalVariableSchema(BaseModel):
    name:str
    type:str
    userId:int
    nodeId:int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True